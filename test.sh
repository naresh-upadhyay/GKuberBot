apiKey="vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A"
secretKey="NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"

payload="symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"

# Sign the request

signature=$(echo -n "$payload" | openssl dgst -shsha256 -hmac "$secretKey")
signature=${signature#*= }    # Keep only the part after the "= "

# Send the request

curl -H "X-MBX-APIKEY: $apiKey" -X POST "https://api.binance.com/api/v3/order?$payload&signature=$signature"
