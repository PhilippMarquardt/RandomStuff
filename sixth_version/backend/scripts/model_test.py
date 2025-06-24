import base64
from app.services.chat_models import model_registry
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage



llm = model_registry.get_model("gpt-4o-mini")


# create a message that has an image in between the texts

image_path = r"C:\Users\pmarq\Downloads\Screenshot 2025-06-18 221252.png"


with open(image_path, "rb") as image_file:
    b64_image = base64.b64encode(image_file.read()).decode()


message = HumanMessage(
    content=[
        {"type": "text", "text": "The name is peter"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is tom"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is kira"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is kira"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is kira"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is kira"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is kira"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is kira"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is kira"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is kira"},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64_image}"},
        },
        {"type": "text", "text": "The name is kira"}
    ]
)
ai_answer = AIMessage(content="Hello")

second_message = HumanMessage(content="How many images do you see")
messages = [message, ai_answer, second_message]
response = llm.invoke(messages)

print(response)







