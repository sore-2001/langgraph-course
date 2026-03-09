from openai import OpenAI

client = OpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="sk-75c3f2f7542747448bc862040b119296"
)

response = client.chat.completions.create(
    model="qwen3.5-flash",
    messages=[{"role": "user", "content": "Hello，who are you "}]
)

print(response.choices[0].message.content)
