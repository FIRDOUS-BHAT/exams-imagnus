import vimeo
import base64
import requests

client_id = 'REDACTED_VIMEO_CLIENT_ID'
secret = 'REDACTED_VIMEO_CLIENT_SECRET'
client = vimeo.VimeoClient(
  token = 'REDACTED_VIMEO_ACCESS_TOKEN',
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