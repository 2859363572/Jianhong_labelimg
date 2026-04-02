import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal


class YOLOPredictor(QObject):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, model_path, class_names=None, conf_threshold=0.25, iou_threshold=0.45):
        super().__init__()
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.class_names = class_names or []
        self.session = None

    def load_model(self):
        try:
            import onnxruntime as ort
            providers = ['CPUExecutionProvider']
            if 'CUDAExecutionProvider' in ort.get_available_providers():
                providers.insert(0, 'CUDAExecutionProvider')
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            input_info = self.session.get_inputs()[0]
            self.input_name = input_info.name
            self.input_shape = input_info.shape
            if len(self.class_names) == 0:
                output_info = self.session.get_outputs()[0]
                num_classes = output_info.shape[-1] - 5 if len(output_info.shape) == 3 else 80
                self.class_names = [f"class_{i}" for i in range(num_classes)]
            return True
        except Exception as e:
            self.error.emit(str(e))
            return False

    def preprocess(self, img_rgb, input_size=640):
        h, w = img_rgb.shape[:2]
        scale = min(input_size / w, input_size / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = np.zeros((input_size, input_size, 3), dtype=np.uint8)
        img_resized = self._resize(img_rgb, new_w, new_h)
        pad_top = (input_size - new_h) // 2
        pad_left = (input_size - new_w) // 2
        resized[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = img_resized
        blob = resized.astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))
        blob = np.expand_dims(blob, axis=0)
        blob = np.ascontiguousarray(blob)
        return blob, scale, pad_left, pad_top

    def _resize(self, img, new_w, new_h):
        h, w = img.shape[:2]
        y_indices = (np.arange(new_h) * (h / new_h)).astype(int)
        x_indices = (np.arange(new_w) * (w / new_w)).astype(int)
        y_indices = np.clip(y_indices, 0, h - 1)
        x_indices = np.clip(x_indices, 0, w - 1)
        return img[np.ix_(y_indices, x_indices)]

    def postprocess(self, outputs, orig_w, orig_h, scale, pad_left, pad_top):
        predictions = outputs[0]
        if len(predictions.shape) == 3:
            predictions = predictions[0]
        detections = []
        for pred in predictions:
            obj_conf = pred[4]
            if obj_conf < self.conf_threshold:
                continue
            class_scores = pred[5:]
            class_id = int(np.argmax(class_scores))
            class_conf = class_scores[class_id]
            confidence = obj_conf * class_conf
            if confidence < self.conf_threshold:
                continue
            cx = (pred[0] - pad_left) / scale
            cy = (pred[1] - pad_top) / scale
            bw = pred[2] / scale
            bh = pred[3] / scale
            x1 = max(0, cx - bw / 2)
            y1 = max(0, cy - bh / 2)
            x2 = min(orig_w, cx + bw / 2)
            y2 = min(orig_h, cy + bh / 2)
            label = self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}"
            detections.append({
                'label': label,
                'points': [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
                'confidence': float(confidence)
            })
        detections = self._nms(detections, self.iou_threshold)
        return detections

    def _nms(self, detections, iou_threshold):
        if len(detections) <= 1:
            return detections
        boxes = []
        for d in detections:
            x1 = d['points'][0][0]
            y1 = d['points'][0][1]
            x2 = d['points'][2][0]
            y2 = d['points'][2][1]
            boxes.append([x1, y1, x2, y2])
        boxes = np.array(boxes)
        scores = np.array([d['confidence'] for d in detections])
        order = scores.argsort()[::-1]
        keep = []
        while len(order) > 0:
            i = order[0]
            keep.append(i)
            if len(order) == 1:
                break
            xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
            yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
            xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
            yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            inter = w * h
            area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
            area_j = (boxes[order[1:], 2] - boxes[order[1:], 0]) * (boxes[order[1:], 3] - boxes[order[1:], 1])
            iou = inter / (area_i + area_j - inter + 1e-6)
            remaining = np.where(iou <= iou_threshold)[0]
            order = order[remaining + 1]
        return [detections[i] for i in keep]

    def predict_image(self, img_rgb):
        if self.session is None:
            return []
        h, w = img_rgb.shape[:2]
        blob, scale, pad_left, pad_top = self.preprocess(img_rgb)
        outputs = self.session.run(None, {self.input_name: blob})
        return self.postprocess(outputs, w, h, scale, pad_left, pad_top)
