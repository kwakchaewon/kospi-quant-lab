"""
한국투자증권 API 토큰 재발급 스크립트
"""

import requests
import json

def get_access_token():
    print("============================================================")
    print("한국투자증권 API 토큰 재발급")
    print("============================================================")
    
    # appkey.txt 읽기
    try:
        with open('appkey.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            app_key = lines[0].strip()
            app_secret = lines[1].strip()
        print(f"APP_KEY: {app_key[:10]}...")
        print(f"APP_SECRET: {app_secret[:10]}...")
    except FileNotFoundError:
        print("ERROR: appkey.txt 파일이 없습니다!")
        return
    
    # 토큰 발급 요청
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret
    }
    
    print("\n토큰 발급 요청 중...")
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            
            if access_token:
                # appkey.txt 업데이트
                with open('appkey.txt', 'w', encoding='utf-8') as f:
                    f.write(f"{app_key}\n")
                    f.write(f"{app_secret}\n")
                    f.write(f"{access_token}\n")
                
                print("\n============================================================")
                print("SUCCESS: 토큰 재발급 완료!")
                print(f"ACCESS_TOKEN: {access_token[:30]}...")
                print("appkey.txt 업데이트 완료")
                print("============================================================")
            else:
                print(f"\nERROR: 토큰을 찾을 수 없습니다.")
                print(f"응답: {data}")
        else:
            print(f"\nERROR: 토큰 발급 실패 (HTTP {response.status_code})")
            print(f"응답: {response.text}")
    
    except Exception as e:
        print(f"\nERROR: {str(e)}")


if __name__ == "__main__":
    get_access_token()
