import streamlit as st
import requests
import asyncio
from shazamio import Shazam
from urllib.parse import urlparse, urlencode
from bs4 import BeautifulSoup

# Function to extract the path from a redirected TikTok URL
def get_redirected_path(url):
    response = requests.get(url)
    if response.status_code == 200:
        return urlparse(response.url).path
    return None

# Function to extract the path from a full TikTok URL
def get_tiktok_path(url):
    parsed_url = urlparse(url)
    path = parsed_url.path

    if parsed_url.netloc == "www.tiktok.com" and path.startswith('/'):
        return path[1:]
    elif parsed_url.netloc == "vt.tiktok.com":
        redirected_path = get_redirected_path(url)
        if redirected_path:
            return redirected_path[1:] if redirected_path.startswith('/') else redirected_path

    return None



# Function to get the last part of the TikTok URL
def get_last_part(base_url, path):
    url = base_url + path
    response = requests.get(url)
    html_content = response.content

    if response.status_code == 200:
        elements = BeautifulSoup(html_content, 'html.parser').find_all('a', {'target': '_self', 'rel': 'opener', 'class': 'epjbyn1 tiktok-v80f7r-StyledLink-StyledLink er1vbsz0'})

        last_part = None
        for element in elements:
            href = element.get('href')
            url_parts = href.split('-')
            last_part = url_parts[-1]

        return last_part

    return None

# Function to get the audio URL
def get_play_url(base_url, path, additional_parameters=None):
    last_part = get_last_part(base_url, path)

    if last_part:
        parameters = {
            'aid': '1988',
            'cookie_enabled': 'true',
            'count': '1',
            'musicID': last_part
        }

        if additional_parameters:
            parameters.update(additional_parameters)

        api_path = 'api/music/item_list/newtab/?' + urlencode(parameters)
        api_url = base_url + api_path

        response = requests.get(api_url)

        if response.status_code == 200:
            json_data = response.json()
            
            item_list = json_data.get('itemList', [])
            for item in item_list:
                music_list = item.get('music', [])
                if music_list:
                    play_url = music_list.get('playUrl')
                    if play_url:
                        url_parts = play_url.split('?')
                        desired_url_part = url_parts[0]
                        return desired_url_part

    return None

# Function to detect the song from the audio URL content
async def detect_song_from_url(play_url):
    try:
        response = requests.get(play_url)
        result = await recognize_song(response.content)
        
        if result and 'track' in result:
            data = result['track']['sections']
            yturl, titlesong = None, None
            for item in data:
                youtube_url = item.get('youtubeurl')
                if youtube_url:
                    youtube_response = requests.get(youtube_url)
                    json_data = youtube_response.json()
                    list_item = json_data.get('actions', [])
                    for youitem in list_item:
                        yturl = youitem.get('uri')
                        judul = youitem.get('share', [])
                        if judul:
                            titlesong = judul.get('text', [])
                        return yturl, titlesong

        # Jika 'track' tidak ada dalam respon atau tidak ada data lagu yang ditemukan
        raise KeyError("Track information not found or song not detected.")

    except Exception as e:
        print(f"Error detecting song: {str(e)}")
        return None, None


# Function to recognize the song from audio content using Shazam
async def recognize_song(file):
    shazam = Shazam()
    return await shazam.recognize_song(file)

# Streamlit app
def main():
    st.title('Detected Music on TikTok ')
    st.caption("Made with 💜  Syukirman Amir")
    st.write("Enter the complete TikTok URL:")
    full_url = st.text_input("Example: https://www.tiktok.com/@username/video/1234567890  OR  https://vt.tiktok.com/12345678/")
    
    if st.button("Detected Music"):
        base_url = 'https://www.tiktok.com/'
        path = get_tiktok_path(full_url)

        if path:
            play_url = get_play_url(base_url, path)
            if play_url:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                yturl, titlesong = loop.run_until_complete(detect_song_from_url(play_url))
                loop.close()

                if yturl and titlesong:
                    st.success(titlesong)
                    st.video(yturl)
                else:
                    st.warning("Couldn't find additional song data.")
            else:
                st.warning("Couldn't find the desired result.")
        else:
            st.error("Please enter a valid TikTok URL.")
    

if __name__ == "__main__":
    main()
