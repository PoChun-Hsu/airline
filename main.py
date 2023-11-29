
import functions_framework
import requests
import json
from datetime import datetime, timedelta
from collections import Counter
import pytz


@functions_framework.http
def main(request):

    # 獲取新的 Access Token
    def get_access_token():
        url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': 'CLIENT_ID',
            'client_secret': 'CLIENT_SECRET'
        }
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()['access_token']
        else:
            raise Exception("Failed to obtain access token")

    # API URL
    api_url = "https://tdx.transportdata.tw/api/basic/v2/Air/FIDS/Airport/Departure/TSA"
    access_token = get_access_token() 
    headers = {
        'Authorization': f'Bearer {access_token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    params = {
        "$format": "JSON",
        "$filter": "DepartureRemark ne '已飛' and DepartureRemark ne '出發'"
    }


    # 當前時間和一定時間內
    taiwan = pytz.timezone('Asia/Taipei')
    current_time = datetime.now(taiwan)
    time_limit = current_time + timedelta(minutes=15)

    # 發送請求
    response = requests.get(api_url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch data: Status code {response.status_code}")
        exit()


    data = response.json()

    # 整理航班資訊
    departure_times = []
    for flight in data:
        estimated_departure = flight.get('ScheduleDepartureTime')
        if estimated_departure:
            estimated_departure_time = taiwan.localize(datetime.strptime(estimated_departure, '%Y-%m-%dT%H:%M'))
            if current_time <= estimated_departure_time <= time_limit:
                departure_times.append(estimated_departure_time.strftime('%H:%M'))

    print(departure_times)
    # 計算每個時間點的航班數量
    flight_count = Counter(departure_times)
    #print(f"flight_count:{flight_count}")
    
    # 只有當有航班預計降落時才發送訊息
    if flight_count:
        message_lines = [
            "注意!!! 未來15分鐘內預期有飛機起飛，時間和班次數：\n"
        ]
        message_lines.extend(f"{time} - {count}班" for time, count in sorted(flight_count.items()))
        message_lines.append("\n祝您有個愉快的一天！")
        message_to_send = "\n".join(message_lines)

        # 您的 Channel Access Token 和 LINE 廣播 API 的部分
        line_headers = {
            'Authorization': 'Bearer ACCESS_TOKEN',
            'Content-Type': 'application/json'
        }

        line_body = {
            'messages': [{
                'type': 'text',
                'text': message_to_send
            }]
        }

        line_response = requests.post('https://api.line.me/v2/bot/message/broadcast', headers=line_headers, data=json.dumps(line_body).encode('utf-8'))

        print(line_response.text)
        return f"message_to_send: {message_to_send}"
    else:
        # 當沒有航班時，不進行任何操作
        return "No flights arriving in the next 15 minutes"
 
