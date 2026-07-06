import os

from openai import OpenAI

# Khởi tạo client với API key của bạn
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

def test_chat():
    try:
        print("Đang gửi request tới OpenAI...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Hoặc "gpt-4" nếu tài khoản của bạn có hỗ trợ
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý AI hữu ích."},
                {"role": "user", "content": "Xin chào, bạn có thể nghe tôi nói không?"}
            ]
        )
        print("\n=== KẾT QUẢ TỪ OPENAI ===")
        print(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    test_chat()
