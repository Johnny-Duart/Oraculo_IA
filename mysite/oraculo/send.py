from wrapper_evolutionapi import SendMessage

client = SendMessage()

response = client.send_message(
    instance="oraculo", number="", text="teste 🚀"
)

print(response.status_code)
print(response.text)
