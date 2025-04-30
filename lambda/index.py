# lambda/index.py
import json
import os
import re
import requests

# ローカル推論サーバーのエンドポイント
LOCAL_INFERENCE_ENDPOINT = os.environ.get("LOCAL_INFERENCE_ENDPOINT", "http://localhost:8000/invoke")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # ローカル推論サーバーへのリクエストペイロード (シンプルな形式を想定)
        request_payload = {
            "messages": messages
            # 必要に応じてmaxTokensなどを追加
        }
        
        print(f"Calling local inference server at {LOCAL_INFERENCE_ENDPOINT} with payload:", json.dumps(request_payload))
        
        # ローカル推論サーバーを呼び出し
        response = requests.post(
            LOCAL_INFERENCE_ENDPOINT,
            headers={"Content-Type": "application/json"},
            json=request_payload
        )
        response.raise_for_status() # HTTPエラーがあれば例外を発生させる
        
        # レスポンスを解析
        response_body = response.json()
        print("Local server response:", json.dumps(response_body, default=str))
        
        # 応答の検証 (ローカルサーバーのレスポンス形式に合わせて調整が必要)
        if not response_body.get('response'): # Assuming the local server returns {"response": "..."}
             raise Exception("No 'response' key found in the local server response")
        
        # アシスタントの応答を取得
        assistant_response = response_body['response'] # Assuming the local server returns {"response": "..."}
        
        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*", # ローカル開発用に "*" を維持。本番環境では適切なオリジンを指定
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except requests.exceptions.RequestException as error: # Catch requests exceptions
        print(f"Local Inference Server Request Error: {str(error)}")
        error_message = f"Failed to connect to local inference server: {str(error)}"
    except Exception as error:
        print("Error:", str(error))
        error_message = str(error) # General error message
        
    return {
        "statusCode": 500,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "OPTIONS,POST"
        },
        "body": json.dumps({
            "success": False,
            "error": error_message # Use the specific error message
        })
    }
