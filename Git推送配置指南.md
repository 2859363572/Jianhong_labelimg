# Git 推送配置指南

## 问题背景

在 Windows 环境下，浏览器可以正常访问 GitHub，但 `git push` 提示连接超时（端口 22/443 均被拦截）。原因是 git 命令行不会自动使用系统代理。

## 解决步骤

### 1. 查找系统代理地址

打开 PowerShell，执行：

```powershell
Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" | Select-Object ProxyEnable, ProxyServer
```

输出示例：

```
ProxyEnable ProxyServer
----------- -----------
          1 127.0.0.1:7897
```

- `ProxyEnable = 1` 表示代理已开启
- `ProxyServer` 即为代理地址和端口

### 2. 配置 git 使用代理

```powershell
git config --global http.proxy http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```

> 注意：将 `7897` 替换为你实际的代理端口。Clash 默认 7890/7897，v2rayN 默认 10809。

### 3. 推送代码

```powershell
git push origin main
```

### 4. 验证推送结果

```powershell
git log -1 --oneline
```

输出示例：

```
f3766b8 feat: add single-target mode, fast annotate, YOLO/SAM ONNX inference and smart copy
```

浏览器访问 https://github.com/2859363572/Jianhong_labelimg 确认代码已更新。

---

## 补充说明

### 取消代理配置（如需）

```powershell
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### 查看当前 git 代理配置

```powershell
git config --global --get http.proxy
git config --global --get https.proxy
```

### 如果代理端口变了

重新执行步骤 2 即可覆盖旧值。

### SSH 方式替代方案（如果 22 端口可用）

```powershell
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your_email@example.com"

# 查看公钥并复制到 GitHub Settings -> SSH Keys
cat ~/.ssh/id_ed25519.pub

# 切换远程地址为 SSH
git remote set-url origin git@github.com:2859363572/Jianhong_labelimg.git
```

> 本项目中 SSH 22 端口被拦截，因此采用 HTTPS + 代理方案。
