import base64
import io
import os
from typing import Optional

import gradio as gr
import torch
from PIL import Image

from util.utils import (
    check_ocr_box,
    get_caption_model_processor,
    get_som_labeled_img,
    get_yolo_model,
)

# 强制使用 CPU 的设置
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
torch.set_num_threads(4)  # 限制 CPU 线程数
DEVICE = torch.device("cpu")  # 修改设备为 CPU

yolo_model = get_yolo_model(model_path="weights/icon_detect/model.pt")
caption_model_processor = get_caption_model_processor(
    model_name="florence2",
    model_name_or_path="weights/icon_caption_florence",
    device="cpu",  # 确保模型加载到 CPU
)
# caption_model_processor = get_caption_model_processor(model_name="blip2", model_name_or_path="weights/icon_caption_blip2")

MARKDOWN = """
# OmniParser for Pure Vision Based General GUI Agent 🔥
<div>
    <a href="https://arxiv.org/pdf/2408.00203">
        <img src="https://img.shields.io/badge/arXiv-2408.00203-b31b1b.svg" alt="Arxiv" style="display:inline-block;">
    </a>
</div>

OmniParser is a screen parsing tool to convert general GUI screen to structured elements. 
"""


# @spaces.GPU
# @torch.inference_mode()
# @torch.autocast(device_type="cuda", dtype=torch.bfloat16)
def process(
    image_input, box_threshold, iou_threshold, use_paddleocr, imgsz
) -> Optional[Image.Image]:
    try:
        with torch.no_grad():
            image_save_path = "imgs/saved_image_demo.png"
            os.makedirs("imgs", exist_ok=True)
            image_input.save(image_save_path)
            image = Image.open(image_save_path)
            box_overlay_ratio = image.size[0] / 3200
            draw_bbox_config = {
                "text_scale": 0.8 * box_overlay_ratio,
                "text_thickness": max(int(2 * box_overlay_ratio), 1),
                "text_padding": max(int(3 * box_overlay_ratio), 1),
                "thickness": max(int(3 * box_overlay_ratio), 1),
            }

            # 强制使用 EasyOCR
            ocr_bbox_rslt, is_goal_filtered = check_ocr_box(
                image_save_path,
                display_img=False,
                output_bb_format="xyxy",
                goal_filtering=None,
                easyocr_args={"paragraph": False, "text_threshold": 0.9},
                use_paddleocr=False,
            )
            text, ocr_bbox = ocr_bbox_rslt

            # 限制处理图片的大小
            imgsz = min(imgsz, 1280)  # 限制最大尺寸

            dino_labled_img, label_coordinates, parsed_content_list = (
                get_som_labeled_img(
                    image_save_path,
                    yolo_model,
                    BOX_TRESHOLD=box_threshold,
                    output_coord_in_ratio=True,
                    ocr_bbox=ocr_bbox,
                    draw_bbox_config=draw_bbox_config,
                    caption_model_processor=caption_model_processor,
                    ocr_text=text,
                    iou_threshold=iou_threshold,
                    imgsz=imgsz,
                )
            )

            image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))
            print("finish processing")
            parsed_content_list = "\n".join(
                [f"icon {i}: " + str(v) for i, v in enumerate(parsed_content_list)]
            )
            return image, str(parsed_content_list)
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        import traceback

        traceback.print_exc()
        return None, str(e)


with gr.Blocks() as demo:
    gr.Markdown(MARKDOWN)
    with gr.Row():
        with gr.Column():
            image_input_component = gr.Image(type="pil", label="Upload image")
            box_threshold_component = gr.Slider(
                label="Box Threshold", minimum=0.01, maximum=1.0, step=0.01, value=0.05
            )
            iou_threshold_component = gr.Slider(
                label="IOU Threshold", minimum=0.01, maximum=1.0, step=0.01, value=0.1
            )
            imgsz_component = gr.Slider(
                label="Icon Detect Image Size",
                minimum=640,
                maximum=1280,  # 降低最大值
                step=32,
                value=640,
            )
            submit_button_component = gr.Button(value="Submit", variant="primary")
        with gr.Column():
            image_output_component = gr.Image(type="pil", label="Image Output")
            text_output_component = gr.Textbox(
                label="Parsed screen elements", placeholder="Text Output"
            )

    submit_button_component.click(
        fn=process,
        inputs=[
            image_input_component,
            box_threshold_component,
            iou_threshold_component,
            gr.Checkbox(value=False, visible=False),  # 隐藏的 PaddleOCR 选项
            imgsz_component,
        ],
        outputs=[image_output_component, text_output_component],
    )

# demo.launch(debug=False, show_error=True, share=True)
demo.launch(
    share=True,
    server_port=7861,
    server_name="0.0.0.0",
    max_threads=4,  # 限制线程数
)
