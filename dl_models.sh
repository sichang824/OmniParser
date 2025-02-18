#!/bin/bash
# download_weights.sh

# 创建weights目录（如果不存在）
mkdir -p weights

# 删除旧的权重文件（如果存在）
rm -rf weights/icon_detect weights/icon_caption weights/icon_caption_florence

# 安装huggingface_hub（如果还没安装）
pip install huggingface_hub

# 下载模型文件
for f in icon_detect/{train_args.yaml,model.pt,model.yaml} icon_caption/{config.json,generation_config.json,model.safetensors}; do
    huggingface-cli download microsoft/OmniParser-v2.0 "$f" --local-dir weights
done

# 重命名文件夹
mv weights/icon_caption weights/icon_caption_florence

echo "模型下载完成！"
