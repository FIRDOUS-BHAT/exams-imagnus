import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import csv
# Make a request
# url =  "https://exams.imagnus.in/admin/student_enquiries/"
url = "https://wise.com/gb/blog/world-currency-symbols"
page = requests.get(url)
soup = BeautifulSoup(page.content, 'html.parser')
if page:
    print('CONNECTION SUCCESSFULL')
# Create top_items as empty list
all_products = []

# # Extract and store in top_items according to instructions on the left
# '''products = soup.select('div.thumbnail')
# for product in products:
#     name = product.select('h4 > a')[0].text.strip()
#     description = product.select('p.description')[0].text.strip()
#     price = product.select('h4.price')[0].text.strip()
#     reviews = product.select('div.ratings')[0].text.strip()
#     image = product.select('img')[0].get('src')
#
#     all_products.append({
#         "name": name,
#         "description": description,
#         "price": price,``
#         "reviews": reviews,
#         "image": image
#     })
#
#     '''
#
# '''students = soup.select('tr.students_list')
# for product in students:
#     created_at = product.select('td.created_at')[0].text.strip()
#     name = product.select('td.student_name')[0].text.strip()``
#     mobile = product.select('td.student_mobile')[0].text.strip()
#     email = product.select('td.student_email')[0].text.strip()
#     city = product.select('td.student_city')[0].text.strip()
#     course = product.select('td.student_course')[0].text.strip()
#     message = product.select('td.student_message')[0].text.strip()
#
#
#     all_products.append({
#         "created_at": created_at,
#         "name": name,
#         "mobile": mobile,
#         "email": email,
#         "city": city,
#         "course": course,
#         'message': message,
#     })
#
# '''
#
# all_chapters = []
# dsChapters = soup.select('div.row > div.col-md-6 > ul.lists-4')[0]
#
# for chapter in dsChapters:
#
#     if isinstance(chapter, NavigableString):
#         continue
#     if isinstance(chapter, Tag):
#         name = chapter.text.strip()
#
#         all_chapters.append({
#             "chapter name": name,
#
#         })
#
#
#
#
# # keys = all_products[0].keys()
# keys = all_chapters[0].keys()
#
# with open('data_science_index.csv', 'w', newline='') as output_file:
#     dict_writer = csv.DictWriter(output_file, keys)
#     dict_writer.writeheader()
#     dict_writer.writerows(all_chapters)

all_currencies = []
dsChapters = soup.select('tbody')[5]

for eachRow in dsChapters.select('tr'):
    symbol = eachRow.select('td')[0].text.strip()
    currency_code = eachRow.select('td')[3].text.strip()
    
    all_currencies.append({
        'currency_code': currency_code,
        'symbol': symbol
        
    })

keys = all_currencies[0].keys()
with open('currency_symbols.csv', 'a', newline='') as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(all_currencies)
