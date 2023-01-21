from tortoise.expressions import Q
import uvicorn
import os
import boto3
import rich.progress
from tqdm import tqdm
import requests
import subprocess
from fastapi import Body, FastAPI, Request, Response
import http.client
from models import Coupons, Course, Category, CourseCategoryLectures,
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form



router = APIRouter()

ACCESS_KEY = 'AKIAWSYDR36FQBPK43DS'
SECRET_KEY = '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'

s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                  aws_secret_access_key=SECRET_KEY)


async def upload_to_s3(file_path, bucket_name, object_name):
    # get the file size
    file_size = os.path.getsize(file_path)
    # create a progress bar
    with tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024,
              desc='Uploading...', leave=True, miniters=1, ascii=True, disable=None) as pbar:
        # upload the file
        with open(file_path, "rb") as f:
            s3.upload_fileobj(f, bucket_name, object_name,
                              Callback=lambda x: pbar.update(x))


async def each_vimeo_video(link, path, file_name):

    if not os.path.exists(path):
        os.makedirs(path)

    response = requests.get(link, stream=True)

    subprocess.check_call(["attrib", "-r", path])

    with open(path+file_name, "wb") as f:
        print("Downloading %s" % file_name)

        # with httpx.stream("GET", link) as response:

        total = int(response.headers["Content-Length"])
        with rich.progress.Progress(
            "[progress.percentage]{task.percentage:>3.0f}%",
            rich.progress.BarColumn(bar_width=None),
            rich.progress.DownloadColumn(),
            rich.progress.TransferSpeedColumn(),
        ) as progress:
            download_task = progress.add_task(
                "Download", total=total)
            i = 1
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:

                    f.write(chunk)

                    progress.update(
                        download_task, completed=i*1024)
                    i = i+1

    await upload_to_s3(path+file_name, "testing-bucket-s3-uploader",
                       path+file_name, )
    os.remove(path+file_name)

    # with open(path+file_name, "rb") as data:
    #     # Create a progress bar
    #     s3.upload_fileobj(
    #         data, "testing-bucket-s3-uploader",
    #         path+file_name
    #     )


@app.post('/download_video')
async def download_videos():
    print('HERE')
    try:

        conn = http.client.HTTPSConnection("api.vimeo.com")
        payload = ''
        lectures = await CourseCategoryLectures.filter(Q(video_360__isnull=True) | Q(video_540__isnull=True) | Q(video_720__isnull=True)).values('id', 'mobile_video_url', 'video_id', 'video_360', 'video_540', 'video_720')
        # print(lectures)
        new_lectures = np.array(lectures)
        # return new_lectures
        headers = {
            'Authorization': 'bearer 07d29a422ae59fd14a17cbdd840b194b',
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.vimeo.*+json;version=3.4'
        }
        i = 0
        for x in new_lectures:
            if x['video_360'] is None:
                if x['video_id']:

                    conn.request("GET", "/videos/" +
                                 x['video_id'], payload, headers)
                    res = conn.getresponse()
                    data = res.read()
                    # print(json.loads(data))
                    json_response = json.loads(data)

                    # open('video.mp4', 'wb').write(r.content)
                    if 'error' not in json_response:

                        file_name = slugify(json_response['name'])
                        print(file_name, "FILENAME")
                        video_360 = "https://d11qyj7iojumc4.cloudfront.net/transcoded/" + \
                            file_name+"/"+str(360)+".mp4"

                        # print(json_response['download'])

                        async def check_if_object_exists(key):
                            try:
                                s3.get_object(
                                    Bucket="testing-bucket-s3-uploader",
                                    Key=key,
                                )
                                return True
                            except s3.exceptions.NoSuchKey:
                                print("S3 OBJECT CREATED")

                                s3.put_object(
                                    Bucket="testing-bucket-s3-uploader",
                                    Key=key,
                                )
                                return False
                        await CourseCategoryLectures.filter(id=x['id']).update(
                            video_duration=json_response['duration'])
                        for d in json_response['download']:

                            if d['rendition'] == '360p':
                                # if not await check_if_object_exists("transcoded/"+file_name+"/360.mp4"):
                                # link_360 = json_response['download'][2]['link']
                                link_360 = d['link']
                                await each_vimeo_video(link_360, "transcoded/"+file_name+"/", "360.mp4")
                                await CourseCategoryLectures.filter(id=x['id']).update(
                                    video_360=video_360,
                                    video_size_360=d['size']
                                )

            if x['video_540'] is None:
                if x['video_id']:

                    conn.request("GET", "/videos/" +
                                 x['video_id'], payload, headers)
                    res = conn.getresponse()
                    data = res.read()
                    # print(json.loads(data))
                    json_response = json.loads(data)

                    # open('video.mp4', 'wb').write(r.content)
                    if 'error' not in json_response:

                        file_name = slugify(json_response['name'])
                        print(file_name, "FILENAME")

                        video_540 = "https://d11qyj7iojumc4.cloudfront.net/transcoded/" + \
                            file_name+"/"+str(540)+".mp4"

                        # print(json_response['download'])

                        async def check_if_object_exists(key):
                            try:
                                s3.get_object(
                                    Bucket="testing-bucket-s3-uploader",
                                    Key=key,
                                )
                                return True
                            except s3.exceptions.NoSuchKey:
                                print("S3 OBJECT CREATED")
                                s3.put_object(
                                    Bucket="testing-bucket-s3-uploader",
                                    Key=key,
                                )
                                return False
                        await CourseCategoryLectures.filter(id=x['id']).update(
                            video_duration=json_response['duration'])
                        for d in json_response['download']:

                            if d['rendition'] == '540p':
                                # if not await check_if_object_exists("transcoded/"+file_name+"/540.mp4"):
                                # link_540 = json_response['download'][3]['link']
                                link_540 = d['link']
                                await each_vimeo_video(link_540, "transcoded/"+file_name+"/", "540.mp4")
                                await CourseCategoryLectures.filter(id=x['id']).update(
                                    video_540=video_540,
                                    video_size_540=d['size']
                                )

            if x['video_720'] is None:
                if x['video_id']:

                    conn.request("GET", "/videos/" +
                                 x['video_id'], payload, headers)
                    res = conn.getresponse()
                    data = res.read()
                    # print(json.loads(data))
                    json_response = json.loads(data)

                    # open('video.mp4', 'wb').write(r.content)
                    if 'error' not in json_response:

                        file_name = slugify(json_response['name'])
                        print(file_name, "FILENAME")

                        video_720 = "https://d11qyj7iojumc4.cloudfront.net/transcoded/" + \
                            file_name+"/"+str(720)+".mp4"
                        # print(json_response['download'])

                        async def check_if_object_exists(key):
                            try:
                                s3.get_object(
                                    Bucket="testing-bucket-s3-uploader",
                                    Key=key,
                                )
                                return True
                            except s3.exceptions.NoSuchKey:
                                print("S3 OBJECT CREATED")

                                s3.put_object(
                                    Bucket="testing-bucket-s3-uploader",
                                    Key=key,
                                )
                                return False
                        await CourseCategoryLectures.filter(id=x['id']).update(
                            video_duration=json_response['duration'])
                        for d in json_response['download']:

                            if d['rendition'] == '720p':
                                # if not await check_if_object_exists("transcoded/"+file_name+"/720.mp4"):
                                #  link_720 = json_response['download'][1]['link']
                                link_720 = d['link']
                                await each_vimeo_video(link_720, "transcoded/"+file_name+"/", "720.mp4")
                                await CourseCategoryLectures.filter(id=x['id']).update(
                                    video_720=video_720,
                                    video_size_720=d['size']
                                )

    except Exception as ex:
        print(str(ex))
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        playsound('Sweet Ting Ting Ting.mp3')
        print(str(ex))

        return str(ex)
