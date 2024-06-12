from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os
import subprocess

app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')
db = client['yayin_veritabani']
collection = db['yayinlar']
collection.create_index([("baslik", "text"), ("yazarlar", "text"), ("anahtar_kelimeler", "text"), ("ozet", "text")])

@app.route("/")
def index():

    all_publications = collection.find()
    publication_list = []
    for publication in all_publications:
        publication_list.append({
            "baslik": publication["baslik"],
            "link": publication["link"],
            "yazarlar": publication["yazarlar"],
            "yayin_turu": publication["yayin_turu"],
            "yayin_yili": publication["yayin_yili"],
            "yayinci": publication["yayinci"],
            "anahtar_kelimeler": publication["anahtar_kelimeler"],
            "ozet": publication["ozet"],
            "alinti_sayisi": publication["alinti_sayisi"],
            "doi": publication["doi"]
        })
    return render_template("index.html", publications=publication_list)

@app.route('/download_pdf', methods=['GET'])
def download_pdf():
    query = request.args.get('query')
    title = request.args.get('title')
    link = request.args.get('link')
    try:
        save_path = "C:\\Users\\Vahit Yüksel\\Desktop\\python\\yazlabb"
        if link.endswith('.pdf'):
            pdf_response = requests.get(link)
            if pdf_response.status_code == 200:
                pdf_filename = os.path.join(save_path, f"{title}.pdf")  
                with open(pdf_filename, 'wb') as f:
                    f.write(pdf_response.content)
                return f"PDF dosyası başarıyla indirildi: {pdf_filename}"
        else:
            html_content = f"<h1>{title}</h1><p>Link: <a href='{link}'>{link}</a></p>"
            pdf_filename = os.path.join(save_path, f"{title}.pdf")
            subprocess.run(['C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe', '--encoding', 'utf-8', '--quiet', '-', pdf_filename], input=html_content.encode('utf-8'), check=True)
            return f"PDF dosyası başarıyla oluşturuldu: {pdf_filename}"
    except Exception as e:
        return f"Hata oluştu: {e}"

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    url = f"https://scholar.google.com/scholar?q={query}"
    response = requests.get(url)
    if response.status_code == 200:
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        publications = soup.find_all("div", class_="gs_ri")
        publication_list = []
        for publication in publications:
            title = publication.find("h3", class_="gs_rt").text.strip() if publication.find("h3", class_="gs_rt") else None
            link = publication.find("h3", class_="gs_rt").a["href"] if publication.find("h3", class_="gs_rt").a else None
            authors = publication.find("div", class_="gs_a").text.strip() if publication.find("div", class_="gs_a") else None
            pub_type = publication.find("div", class_="gs_a").text.strip().split("-")[-1].strip() if publication.find("div", class_="gs_a") else None
            pub_year = publication.find("div", class_="gs_a").text.strip().split(",")[-1].strip() if publication.find("div", class_="gs_a") else None
            publisher = publication.find("div", class_="gs_a").text.strip().split("-")[-1].strip() if publication.find("div", class_="gs_a") else None
            keywords = publication.find("div", class_="gs_rs").text.strip() if publication.find("div", class_="gs_rs") else None
            abstract = publication.find("div", class_="gs_rs").text.strip() if publication.find("div", class_="gs_rs") else None
            citations = publication.find("div", class_="gs_fl").text.strip() if publication.find("div", class_="gs_fl") else None
            doi = publication.find("div", class_="gs_or_ggsm").text.strip() if publication.find("div", class_="gs_or_ggsm") else None
            yayin_verisi = {
                "baslik": title,
                "link": link,
                "yazarlar": authors,
                "yayin_turu": pub_type,
                "yayin_yili": pub_year,
                "yayinci": publisher,
                "anahtar_kelimeler": keywords,
                "ozet": abstract,
                "alinti_sayisi": citations,
                "doi": doi,
                "query": query  
            }
            collection.insert_one(yayin_verisi)
        publication_list = [{
            "baslik": title,
            "link": link,
            "yazarlar": authors,
            "yayin_turu": pub_type,
            "yayin_yili": pub_year,
            "yayinci": publisher,
            "anahtar_kelimeler": keywords,
            "ozet": abstract,
            "alinti_sayisi": citations,
            "doi": doi
        } for title, link, authors, pub_type, pub_year, publisher, keywords, abstract, citations, doi in zip(
            [publication.find("h3", class_="gs_rt").text.strip() for publication in publications],
            [publication.find("h3", class_="gs_rt").a["href"] if publication.find("h3", class_="gs_rt").a else None for publication in publications],
            [publication.find("div", class_="gs_a").text.strip() if publication.find("div", class_="gs_a") else None for publication in publications],
            [publication.find("div", class_="gs_a").text.strip().split("-")[-1].strip() if publication.find("div", class_="gs_a") else None for publication in publications],
            [publication.find("div", class_="gs_a").text.strip().split(",")[-1].strip() if publication.find("div", class_="gs_a") else None for publication in publications],
            [publication.find("div", class_="gs_a").text.strip().split("-")[-1].strip() if publication.find("div", class_="gs_a") else None for publication in publications],
            [publication.find("div", class_="gs_rs").text.strip() if publication.find("div", class_="gs_rs") else None for publication in publications],
            [publication.find("div", class_="gs_rs").text.strip() if publication.find("div", class_="gs_rs") else None for publication in publications],
            [publication.find("div", class_="gs_fl").text.strip() if publication.find("div", class_="gs_fl") else None for publication in publications],
            [publication.find("div", class_="gs_or_ggsm").text.strip() if publication.find("div", class_="gs_or_ggsm") else None for publication in publications]
        )]
        return render_template("search_results.html", query=query, publications=publication_list)
    else:
        return "Arama başarısız oldu."

if __name__ == '__main__':
    app.run(debug=True)
