import numpy as np
from PyQt5.QtCore import QPointF


class SAMOnnxPredictor:
    def __init__(self, encoder_path, decoder_path):
        self.encoder_path = encoder_path
        self.decoder_path = decoder_path
        self.encoder_session = None
        self.decoder_session = None
        self.image_embedding = None
        self.input_size = 1024
        self.orig_size = None

    def load_model(self):
        import onnxruntime as ort
        providers = ['CPUExecutionProvider']
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            providers.insert(0, 'CUDAExecutionProvider')
        self.encoder_session = ort.InferenceSession(self.encoder_path, providers=providers)
        self.decoder_session = ort.InferenceSession(self.decoder_path, providers=providers)
        input_info = self.encoder_session.get_inputs()[0]
        shape = input_info.shape
        if len(shape) == 4:
            self.input_size = shape[-1] if isinstance(shape[-1], int) and shape[-1] > 0 else 1024
        return True

    def set_image(self, img_rgb):
        self.orig_size = img_rgb.shape[:2]
        blob = self._preprocess(img_rgb)
        input_name = self.encoder_session.get_inputs()[0].name
        self.image_embedding = self.encoder_session.run(None, {input_name: blob})[0]

    def _preprocess(self, img_rgb):
        h, w = img_rgb.shape[:2]
        scale = min(self.input_size / w, self.input_size / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = np.zeros((self.input_size, self.input_size, 3), dtype=np.float32)
        img_resized = self._resize(img_rgb, new_w, new_h)
        pad_top = (self.input_size - new_h) // 2
        pad_left = (self.input_size - new_w) // 2
        resized[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = img_resized
        pixel_mean = np.array([123.675, 116.28, 103.53], dtype=np.float32)
        pixel_std = np.array([58.395, 57.12, 57.375], dtype=np.float32)
        resized = (resized - pixel_mean) / pixel_std
        blob = np.transpose(resized, (2, 0, 1))
        blob = np.expand_dims(blob, axis=0).astype(np.float32)
        return np.ascontiguousarray(blob)

    def _resize(self, img, new_w, new_h):
        h, w = img.shape[:2]
        y_indices = np.clip((np.arange(new_h) * (h / new_h)).astype(int), 0, h - 1)
        x_indices = np.clip((np.arange(new_w) * (w / new_w)).astype(int), 0, w - 1)
        return img[np.ix_(y_indices, x_indices)]

    def predict_box(self, box_xyxy):
        if self.image_embedding is None:
            return None
        orig_h, orig_w = self.orig_size
        input_w, input_h = self.input_size, self.input_size
        scale_x = input_w / orig_w
        scale_y = input_h / orig_h
        box = np.array([
            box_xyxy[0] * scale_x,
            box_xyxy[1] * scale_y,
            box_xyxy[2] * scale_x,
            box_xyxy[3] * scale_y
        ], dtype=np.float32).reshape(1, 4)

        inputs = {}
        for inp in self.decoder_session.get_inputs():
            if 'embedding' in inp.name.lower() or 'features' in inp.name.lower():
                inputs[inp.name] = self.image_embedding
            elif 'box' in inp.name.lower() or 'bbox' in inp.name.lower():
                inputs[inp.name] = box
            elif 'point' in inp.name.lower():
                inputs[inp.name] = np.zeros((1, 0, 2), dtype=np.float32)
            elif 'label' in inp.name.lower():
                inputs[inp.name] = np.zeros((1, 0), dtype=np.float32)
            elif 'mask' in inp.name.lower() and 'input' in inp.name.lower():
                inputs[inp.name] = np.zeros((1, 1, 256, 256), dtype=np.float32)
            elif 'has_mask' in inp.name.lower():
                inputs[inp.name] = np.zeros((1,), dtype=np.float32)

        try:
            outputs = self.decoder_session.run(None, inputs)
            mask = outputs[0]
            if len(mask.shape) == 4:
                mask = mask[0, 0]
            elif len(mask.shape) == 3:
                mask = mask[0]
            mask = (mask > 0).astype(np.uint8)
            return mask
        except Exception as e:
            print(f"SAM decode error: {e}")
            return None

    def mask_to_bbox(self, mask):
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        if not rows.any():
            return None
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        orig_h, orig_w = self.orig_size
        mask_h, mask_w = mask.shape
        x1 = cmin * orig_w / mask_w
        y1 = rmin * orig_h / mask_h
        x2 = (cmax + 1) * orig_w / mask_w
        y2 = (rmax + 1) * orig_h / mask_h
        return [x1, y1, x2, y2]

    def mask_to_points(self, mask):
        contours = self._find_contours(mask)
        if not contours:
            return None
        largest = max(contours, key=len)
        if len(largest) < 4:
            return None
        step = max(1, len(largest) // 16)
        sampled = largest[::step]
        orig_h, orig_w = self.orig_size
        mask_h, mask_w = mask.shape
        points = []
        for y, x in sampled:
            px = x * orig_w / mask_w
            py = y * orig_h / mask_h
            points.append((px, py))
        points.append(points[0])
        return points

    def _find_contours(self, mask):
        h, w = mask.shape
        padded = np.zeros((h + 2, w + 2), dtype=np.uint8)
        padded[1:-1, 1:-1] = mask
        contours = []
        visited = np.zeros_like(padded, dtype=bool)
        for y in range(1, h + 1):
            for x in range(1, w + 1):
                if padded[y, x] and not visited[y, x]:
                    contour = []
                    stack = [(y, x)]
                    while stack:
                        cy, cx = stack.pop()
                        if cy < 1 or cy > h or cx < 1 or cx > w:
                            continue
                        if visited[cy, cx] or not padded[cy, cx]:
                            continue
                        visited[cy, cx] = True
                        border = False
                        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = cy + dy, cx + dx
                            if not padded[ny, nx]:
                                border = True
                                break
                        if border:
                            contour.append((cy - 1, cx - 1))
                        stack.extend([(cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)])
                    if contour:
                        contours.append(contour)
        return contours
