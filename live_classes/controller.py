import vimeo
import base64
import requests

client_id = '150f7656a3504dd937ad5090e04c93c3ac296921'
secret = 'LTF72ZT8VISRKI2mWUHq9mTtA5AMh/KvZd+3uPfsjq28/5VtzJYDSpWECFuqh5sktzeqLuJny+c572ys47p3MWLJ9jUOgEbrUSzwfoRiD+fLxuTiPWha7INM/vY5VPjD'
client = vimeo.VimeoClient(
  token='e28a1f3581eabc96bc4f25a04a5b5a6d',
  key=client_id,
  secret= secret
)

# response = client.get(uri)
# print(response.json())
print(client)

# Standard Base64 Encoding

x = client_id.encode("utf-8")
y = secret.encode("utf-8")
encodedBytes = base64.b64encode(x+y)
encodedStr = str(encodedBytes, "utf-8")

print(encodedStr)

url = 'https://api.vimeo.com/me'

headers = {
            "Accept": "application/vnd.vimeo.*+json;version=3.4",
            "Authorization": "bearer "+encodedStr
        }

response = requests.request("GET", url, headers=headers)

print(response)