import gradio as gr
from gradio_client import Client

# Hugging Face ka sabse tez active Text-to-Video Free Public Space Pipeline
PUBLIC_GPU_SPACE = "Kijai/CogVideoX-Wrapper"


def generate_video_fast(prompt):
    if not prompt:
        return None

    print(f"Connecting to Public GPU pipeline for prompt: '{prompt}'...")

    try:
        client = Client(PUBLIC_GPU_SPACE)
        result = client.predict(
            prompt=prompt,
            negative_prompt="low quality, blurry, distorted, low resolution",
            num_inference_steps=25,
            guidance_scale=6.0,
            seed=-1,
            api_name="/generate_video",
        )

        if isinstance(result, (tuple, list)):
            video_path = result[0]
        else:
            video_path = result

        print(f"Video generated successfully! Path: {video_path}")
        return video_path

    except Exception as e:
        print(f"Pipeline redirect error: {str(e)}")
        raise gr.Error("Hugging Face Public Server Busy hai bhai! Ek baar dobara button dabayein.")


with gr.Blocks() as demo:
    gr.Markdown("# APEXCODE 3 - Ultra Fast Free Video Suite")
    gr.Markdown("Generates stunning AI videos via high-speed public GPU clusters. Developed by Apex.")

    with gr.Row():
        with gr.Column():
            prompt_input = gr.Textbox(
                label="Enter your Video Prompt",
                placeholder="A futuristic sports car racing on a cyber highway at night, neon reflections, 4k cinematic...",
                lines=3,
            )
            generate_btn = gr.Button("Generate Video (Takes ~30-60 Seconds)", variant="primary")

        with gr.Column():
            output_video = gr.Video(label="Generated AI Video Output")

    generate_btn.click(
        fn=generate_video_fast,
        inputs=prompt_input,
        outputs=output_video,
    )


if __name__ == "__main__":
    demo.launch()
