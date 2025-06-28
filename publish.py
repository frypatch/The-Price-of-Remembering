import markdown # version 3.1
from titlecase import titlecase # version 2.4
import os
from xml.dom import minidom
import zipfile
import sys
import json
import re
import datetime
import hashlib
from xhtml2pdf import pisa

##########################################################
## mark2epub
## https://github.com/AlexPof/mark2epub
## mark2epub is a simple Python script for converting Markdown files, images, and css files to a single ePub book.


##########################################################
## global variables
work_dir = "book"
build_dir = "published_versions"
release_dir = "releases"
today = datetime.date.today()
publish_date = datetime.date.today().strftime('%Y-%m-%d')
publish_version = """{}.{}.{}""".format(
    today.year-2022, 
    str(today.month).zfill(2), 
    str(today.day).zfill(2))
with open(os.path.join(work_dir,"description.json"),"r") as f:
    json_metadata = json.load(f)["metadata"]
dc_description = json_metadata["dc:description"].replace('"', '')
dc_title = json_metadata["dc:title"].replace('"', '')
dc_creator = json_metadata["dc:creator"].replace('"', '')
dc_subject = json_metadata["dc:subject"].replace('"', '')
dc_rights = json_metadata["dc:rights"].replace('"', '')
dc_publisher = json_metadata["dc:publisher"].replace('"', '')
dc_source = json_metadata["dc:source"]
output_filename = dc_title.replace('"', '').replace("'", "").replace(";", "").replace(":", "").replace(",", "").replace(" ", ".")
isbn = hashlib.sha1((output_filename + ".-.V" + publish_version).encode()).hexdigest()
website = dc_source

##########################################################
## called from __main__
## creates and wites the files.
def publish():
    ######################################################
    ## Now creating build directory (if it doesn't exist)
    if not os.path.exists(build_dir):
      os.makedirs(build_dir)
    ######################################################
    ## Now updating book/CONTENTS.md
    update_md_contents()
    ######################################################
    ## Now updating README.md
    update_md_readme()
    ######################################################
    ## Now updating the sitemap
    update_xml_sitemap()
    ######################################################
    ## Now creating the text book
    publish_txt_book()
    ######################################################
    ## Now creating the makrdown book
    publish_md_book()
    ######################################################
    ## Now creating the HTML book
    publish_html_book()
    ######################################################
    ## Now creating the ePUB book
    publish_epub_book()
    ######################################################
    ## Now creating the PDF book
    publish_pdf_book()
    ######################################################
    ## Success!
    print("INFO: eBook creation complete")


##########################################################
def update_md_contents():
    ######################################################
    ## Create MD Table of contents
    toc_md = """# CONTENTS.\n"""
    toc_md += """\n\n"""
    toc_md += """* [*Cover Page*](Cover_Page.md).\n"""
    for entry in get_TOC_dict()["entries"]:
        filename = entry["filename"]
        titles = ". ".join(entry["titles"])
        link = """{}.md""".format(filename)
        if filename.startswith("CHAPTER"):
            toc_md += """* [{}]({}).""".format(titles,link)
        else:
            toc_md += """* [*{}*]({}).""".format(titles,link)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            toc_md += """ {}.""".format(titlecase(subtitle.lower()))
        toc_md += """\n"""
    ######################################################
    ## Now updating book/CONTENTS.md
    book_toc_md_file = open(os.path.join(work_dir, "Contents.md"), "w")
    book_toc_md_file.write(toc_md)
    book_toc_md_file.close()


##########################################################
def update_md_readme():
    ######################################################
    ## Create MD README Table of contents
    toc_md = """# CONTENTS.\n"""
    toc_md += """\n\n"""
    toc_md += """* [*Cover Page*](book/Cover_Page.md).\n"""
    for entry in get_TOC_dict()["entries"]:
        filename = entry["filename"]
        titles = ". ".join(entry["titles"])
        link = """book/{}.md""".format(filename)
        if filename.startswith("CHAPTER"):
            toc_md += """* [{}]({}).""".format(titles,link)
        else:
            toc_md += """* [*{}*]({}).""".format(titles,link)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            toc_md += """ {}.""".format(titlecase(subtitle.lower()))
        toc_md += """\n"""
    ######################################################
    ## Now creating README.md
    md_page_break = "\n\n\n\n\n"
    md_data = ""
    md_data += """![{}](book/images/cover.jpg)

# THE PRICE OF REMEMBERING

**OR,**

# THE DOORS OF STONE SPECULATIVE MUSINGS

## THE KINGKILLER CHRONICLE DAY THREE

**{}**

**VERSION {}**

## THE KINGKILLER CHRONICLE

**DAY ONE: THE NAME OF THE WIND**

**DAY TWO: THE WISE MAN'S FEAR**

**DAY THREE: THE PRICE OF REMEMBERING**\n""".format(dc_title, dc_creator.upper(), publish_version)
    md_data += md_page_break
    md_data += "#" + get_chapter_MD("Legal_Disclaimer.md").strip('\n') + "\n"
    md_data += md_page_break
    md_data += "#" + get_chapter_MD("Acknowledgements.md").strip('\n') + "\n"
    md_data += md_page_break
    md_data += "#" + get_chapter_MD("Forward.md").strip('\n') + "\n"
    md_data += md_page_break
    md_data += "#" + get_chapter_MD("Resources.md").strip('\n') + "\n"
    md_data += md_page_break
    md_data += "#" + toc_md.strip('\n') + "\n"
    md_file = open("README.md", "w")
    md_file.write(md_data)
    md_file.close()


##########################################################
def update_xml_sitemap():
    ## Now updating the sitemap
    sitemap_file = open("sitemap.xml", "w")
    sitemap_file.write(get_sitemap_XML())
    sitemap_file.close()


##########################################################
def get_all_filenames(the_dir,extensions=[]):
    all_files = [x for x in os.listdir(the_dir)]
    all_files = [x for x in all_files if x.split(".")[-1] in extensions]
    return all_files


##########################################################
def publish_txt_book():
    ######################################################
    ## Create TXT Book Table of contents
    toc_txt = """CONTENTS.\n"""
    toc_txt += """\n\n"""
    for entry in get_TOC_dict()["entries"]:
        filename = entry["filename"]
        xhtml = entry["xhtml"]
        titles = ". ".join(entry["titles"])
        toc_txt +="""    {}.""".format(titles)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            toc_txt += """ {}.""".format(titlecase(subtitle.lower()))
        toc_txt += """\n"""
    ######################################################
    ## Now creating the TXT book
    txt_data = ""
    for chapter_md_filename in chapter_md_filenames():
        if chapter_md_filename == "Contents.md":
            ## Generate Table of Contents from description.json
            txt_data += toc_txt
        else:
            markdown_data = get_chapter_MD(chapter_md_filename)
            txt_data += get_chapter_TXT(markdown_data)
        txt_data += "\n\n\n\n"
    txt_data = txt_data.replace("“", '"')
    txt_data = txt_data.replace("”", '"')
    txt_data = txt_data.replace("‘", "'")
    txt_data = txt_data.replace("’", "'")
    txt_data = txt_data.replace("–", "-")
    txt_data = txt_data.replace("—", "-")
    txt_data = txt_data.replace("…", "...")
    txt_data = txt_data.replace("* * *", "***")
    txt_file = open(os.path.join(release_dir, output_filename + ".txt"), "w")
    txt_file.write(txt_data)
    txt_file.close()


##########################################################
def publish_md_book():
    ######################################################
    ## Create MD Book Table of contents
    toc_md = """# CONTENTS.\n"""
    toc_md += """\n\n"""
    toc_md += """* [*Cover*](#).\n"""
    for entry in get_TOC_dict()["entries"]:
        filename = entry["filename"]
        titles = ". ".join(entry["titles"])
        link = "#" + entry["titles"][0].replace(" ","-").lower()
        if filename.startswith("CHAPTER"):
            toc_md += """* [{}]({}).""".format(titles,link)
        else:
            toc_md += """* [*{}*]({}).""".format(titles,link)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            toc_md += """ {}.""".format(titlecase(subtitle.lower()))
        toc_md += """\n"""
    ######################################################
    ## Now creating the MD book
    md_page_break = "\n\n\n\n--------------------\n\n\n\n"
    md_data = ""
    md_data += """![Cover]({}book/images/cover.jpg)""".format(website)
    md_data += md_page_break
    for chapter_md_filename in chapter_md_filenames():
        if chapter_md_filename == "Contents.md":
            md_data += get_chapter_MD("Resources.md").strip('\n')
            md_data += md_page_break
            md_data += toc_md.strip('\n')
        else:
            md_data += get_chapter_MD(chapter_md_filename).strip('\n')
        md_data += md_page_break
    md_data = md_data.replace("“", '"')
    md_data = md_data.replace("”", '"')
    md_data = md_data.replace("‘", "'")
    md_data = md_data.replace("’", "'")
    md_data = md_data.replace("–", "-")
    md_data = md_data.replace("—", "-")
    md_data = md_data.replace("…", "...")
    md_file = open(os.path.join(release_dir, output_filename + ".md.txt"), "w")
    md_file.write(md_data)
    md_file.close()


##########################################################
def publish_html_book():
    ######################################################
    ## Create the HTML book CSS
    all_css = ""
    for css_filename in ["general", "chapter", "webpage", "palettes"]:
        with open(os.path.join(work_dir, "css", css_filename + ".css"),"r") as some_css:
            all_css += some_css.read().strip() + "\n"
    ######################################################
    ## Create HTML Book Table of contents
    toc_md = """# CONTENTS.\n"""
    toc_md += """\n"""
    toc_md += """* [*Cover*](#).\n"""
    toc_md += """* [*Settings*](#Settings).\n"""
    for entry in get_TOC_dict()["entries"]:
        filename = entry["filename"]
        titles = ". ".join(entry["titles"])
        link = "#" + filename
        if filename.startswith("CHAPTER"):
            toc_md += """* [{}]({}).""".format(titles,link)
        else:
            toc_md += """* [*{}*]({}).""".format(titles,link)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            toc_md += """ {}.""".format(titlecase(subtitle.lower()))
        toc_md += """\n"""
    ######################################################
    ## Create rich snippets for Google
    rich_snippet = '''<!-- rich snippet for an eBook -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Book",
  "name": "''' + dc_title + '''",
  "author": {
    "@type": "Person",
    "name": "''' + dc_creator + '''"
  },
  "datePublished": "''' + publish_date + '''",
  "description": "''' + dc_description + '''",
  "genre": "''' + dc_subject + '''",
  "license": "''' + dc_rights + '''",
  "isbn": "''' + isbn + '''",
  "publisher": {
    "@type": "Organization",
    "name": "''' + dc_publisher + '''"
  },
  "image": "''' + website + '''book/images/cover.jpg",
  "bookFormat": "https://schema.org/EBook",
  "offers": {
    "@type": "Offer",
    "url": "''' + website + '''",
    "price": "0.00",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock"
  }
}
</script>'''
    ######################################################
    ## Now creating the HTML book
    html_page_anchor_template = """<a name="{}"></a>"""
    html_data = '''<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="ISO-8859-1">
<title>'''+ dc_title + '''</title>
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="''' + dc_description + '''">
''' + rich_snippet + '''
<style>
''' + all_css + '''
</style>
<script>
function store_palette() {
   if (localStorage.getItem('palette') == 'night') {
     localStorage.setItem('palette', 'day');
   } else {
     localStorage.setItem('palette', 'night');
   }
}
function display_palette() {
   var element = document.body;
   var currentPalette = element.classList.contains("night-palette") ? "night" : "day"
   var storedPalette = localStorage.getItem('palette') || 'day'
   if (currentPalette != storedPalette) {
     element.classList.toggle("night-palette");
   }
}
</script>
</head>
<body>
<script>
    display_palette();
</script>
<a name="Cover"></a>
<picture>
  <source srcset="''' + website + '''book/media/cover.avif" type="image/avif">
  <source srcset="''' + website + '''book/images/cover.jpg" type="image/jpeg">
  <img class="book_cover" src="''' + website + '''book/media/cover.png" alt="Cover">
</picture>
<hr />
<a name="Settings"></a>
<button onclick="store_palette();display_palette();">Toggle Dark Mode</button>
<hr />'''
    for chapter_md_filename in chapter_md_filenames():
        if chapter_md_filename == "Contents.md":
            html_data += "\n" + html_page_anchor_template.format("resources")
            html_data += "\n" + get_chapter_HTML(get_chapter_MD("Resources.md"))
            html_data += "\n<hr />"
            html_data += "\n" + html_page_anchor_template.format("contents")
            html_data += "\n" + get_chapter_HTML(toc_md)
            html_data += "\n<main>"
        else:
            filename, extension = os.path.splitext(chapter_md_filename)
            html_data += "\n" + html_page_anchor_template.format(filename)
            html_data += "\n" + get_chapter_HTML(get_chapter_MD(chapter_md_filename))
        html_data += "\n<hr />"
    html_data += "\n</main>"
    html_data += "\n</body>"
    html_data += "\n</html>"
    html_data = html_data.replace("“", "&ldquo;")
    html_data = html_data.replace("”", "&rdquo;")
    html_data = html_data.replace("‘", "&lsquo;")
    html_data = html_data.replace("’", "&rsquo;")
    html_data = html_data.replace("–", "&mdash;")
    html_data = html_data.replace("—", "&mdash;")
    html_data = html_data.replace("…", "&hellip;")
    html_file = open("index.html", "w")
    html_file.write(html_data)
    html_file.close()
    html_file = open(os.path.join(build_dir, output_filename + ".-.V" + publish_version + ".html"), "w")
    html_file.write(html_data)
    html_file.close()

##########################################################
def publish_pdf_book():
    ######################################################
    ## Create the HTML book CSS
    all_css = ""
    for css_filename in ["general", "chapter", "webpage", "pdf"]:
        with open(os.path.join(work_dir, "css", css_filename + ".css"),"r") as some_css:
            all_css += some_css.read().strip() + "\n"
    ######################################################
    ## Now creating the HTML book
    html_data_page_break = "<pdf:nextpage></pdf:nextpage>\n"
    html_page_anchor_template = html_data_page_break + """<a name="{}"></a>"""
    html_toc = '''
<h1><big>C</big>ontents.</h1>
<div>
    <pdf:toc></pdf:toc>
</div>'''
    html_data = '''<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="ISO-8859-1">
<style>
''' + all_css + '''
@page {
    size: a5 portrait;
    background-image: url("''' + os.path.abspath(os.path.join("book", "images", "cover.jpg")) + '''");
    background-width: 148mm; /* A5 width */
    background-height: 210mm; /* A5 height */
    background-page-step: 10000;
    margin: .5in;
}
</style>
</head>
<body>
<a name="Cover"></a>
'''
    for chapter_md_filename in chapter_md_filenames():
        filename, extension = os.path.splitext(chapter_md_filename)
        html_data += "\n" + html_page_anchor_template.format(filename)
        if chapter_md_filename == "Contents.md":
            html_data += html_toc
        else:
            html_data += "\n" + get_chapter_HTML(get_chapter_MD(chapter_md_filename))
    html_data += "\n</body>"
    html_data += "\n</html>"
    html_data = html_data.replace("“", "&ldquo;")
    html_data = html_data.replace("”", "&rdquo;")
    html_data = html_data.replace("‘", "&lsquo;")
    html_data = html_data.replace("’", "&rsquo;")
    html_data = html_data.replace("–", "&mdash;")
    html_data = html_data.replace("—", "&mdash;")
    html_data = html_data.replace("…", "&hellip;")
    with open(os.path.join(build_dir, output_filename + ".-.V" + publish_version + ".pdf"), "wb") as file:
        pdf = pisa.CreatePDF(html_data, file)

##########################################################
def publish_epub_book():
    images_dir = os.path.join(work_dir, "images")
    css_dir = os.path.join(work_dir, "css")

    ## Reading the JSON file containing the description of the eBook
    ## and compiling the list of relevant Markdown, CSS, and image files

    with open(os.path.join(work_dir,"description.json"),"r") as f:
        json_data = json.load(f)

    all_md_filenames=[]
    all_css_filenames=json_data["default_css"][:]
    for chapter in json_data["chapters"]:
        if not chapter["markdown"] in all_md_filenames:
            all_md_filenames.append(chapter["markdown"])
        if len(chapter["css"]) and (not chapter["css"] in all_css_filenames):
            all_css_filenames.append(chapter["css"])
    all_image_filenames = get_all_filenames(images_dir,extensions=["gif","jpg","jpeg","png"])

    ######################################################
    ## Create ePUB Book Table of contents
    toc_md = """# CONTENTS.\n"""
    toc_md += """\n"""
    toc_md += """* [*Cover*](titlepage.xhtml).\n"""
    for entry in get_TOC_dict()["entries"]:
        filename = entry["filename"]
        xhtml = entry["xhtml"]
        titles = ". ".join(entry["titles"])
        if filename.startswith("CHAPTER"):
            toc_md += """* [{}]({}).""".format(titles,xhtml)
        else:
            toc_md += """* [*{}*]({}).""".format(titles,xhtml)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            toc_md += """ {}.""".format(titlecase(subtitle.lower()))
        toc_md += """\n"""
    ######################################################
    ## Now creating the ePUB book
    with zipfile.ZipFile(os.path.join(build_dir, output_filename + ".-.V" + publish_version + ".epub"), "w" ) as myZipFile:

        ## First, write the mimetype
        myZipFile.writestr("mimetype","application/epub+zip", zipfile.ZIP_DEFLATED )

        ## Then, the file container.xml which just points to package.opf
        container_data = get_container_XML()
        myZipFile.writestr("META-INF/container.xml",container_data, zipfile.ZIP_DEFLATED )

        ## Then, the package.opf file itself
        package_data = get_packageOPF_XML(md_filenames=all_md_filenames,
                                          image_filenames=all_image_filenames,
                                          css_filenames=all_css_filenames,
                                          description_data=json_data
                                         )
        myZipFile.writestr("OPS/package.opf",package_data, zipfile.ZIP_DEFLATED)

        ## First, we create the cover page
        coverpage_data = get_coverpage_XML(json_data["cover_image"])
        myZipFile.writestr("OPS/titlepage.xhtml",coverpage_data.encode('utf-8'),zipfile.ZIP_DEFLATED)

        ## Now, we are going to convert the Markdown files to xhtml files
        for i,chapter in enumerate(json_data["chapters"]):
            chapter_md_filename = chapter["markdown"]
            chapter_css_filenames = json_data["default_css"][:]
            if len(chapter["css"]):
                chapter_css_filenames.append(chapter["css"])

            chapter_data = ""
            if chapter_md_filename == "Contents.md":
                chapter_data = get_chapter_XML(toc_md,chapter_css_filenames)
            else:
                markdown_data = get_chapter_MD(chapter_md_filename)
                chapter_data = get_chapter_XML(markdown_data,chapter_css_filenames)
            myZipFile.writestr("OPS/s{:05d}-{}.xhtml".format(i,chapter_md_filename.split(".")[0]),
                               chapter_data.encode('utf-8'),
                               zipfile.ZIP_DEFLATED)


        ## Writing the TOC.xhtml file
        toc_xml_data = get_TOC_XML(json_data["default_css"])
        myZipFile.writestr("OPS/TOC.xhtml",toc_xml_data.encode('utf-8'),zipfile.ZIP_DEFLATED)

        ## Writing the TOC.ncx file
        toc_ncx_data = get_TOCNCX_XML()
        myZipFile.writestr("OPS/toc.ncx",toc_ncx_data.encode('utf-8'),zipfile.ZIP_DEFLATED)

        ## Copy image files
        for i,image_filename in enumerate(all_image_filenames):
            with open(os.path.join(images_dir,image_filename),"rb") as f:
                filedata = f.read()
            myZipFile.writestr("OPS/images/{}".format(image_filename),
                               filedata,
                               zipfile.ZIP_DEFLATED)

        ## Copy CSS files
        for i,css_filename in enumerate(all_css_filenames):
            with open(os.path.join(css_dir,css_filename),"rb") as f:
                filedata = f.read()
            myZipFile.writestr("OPS/css/{}".format(css_filename),
                               filedata,
                               zipfile.ZIP_DEFLATED)

def get_packageOPF_XML(md_filenames=[],image_filenames=[],css_filenames=[],description_data=None):

    doc = minidom.Document()

    package = doc.createElement('package')
    package.setAttribute('xmlns',"http://www.idpf.org/2007/opf")
    package.setAttribute('version',"3.0")
    package.setAttribute('xml:lang',"en")
    package.setAttribute("unique-identifier","pub-id")

    ## Now building the metadata

    metadata = doc.createElement('metadata')
    metadata.setAttribute('xmlns:dc', 'http://purl.org/dc/elements/1.1/')

    ## Add book id
    dc_identifier = doc.createElement("dc:identifier")
    dc_identifier.setAttribute("id", "book-id")
    dc_identifier.appendChild(doc.createTextNode(isbn))
    metadata.appendChild(dc_identifier)

    ## Add publish date
    dc_identifier = doc.createElement("dc:date")
    dc_identifier.appendChild(doc.createTextNode(publish_date))
    metadata.appendChild(dc_identifier)

    ## Add metadata from description.json
    for k,v in description_data["metadata"].items():
        if k in ["dc:identifier", "dc:date"]:
            print("""WARN: {} is set in both the description.json and automatically generated in publish.py.""".format(k))
        if len(v):
            x = doc.createElement(k)
            for metadata_type,id_label in [("dc:title","title"),("dc:creator","creator")]:
                if k==metadata_type:
                    x.setAttribute('id',id_label)
            x.appendChild(doc.createTextNode(v))
            metadata.appendChild(x)


    ## Now building the manifest

    manifest = doc.createElement('manifest')

    ## TOC.xhtml file for EPUB 3
    x = doc.createElement('item')
    x.setAttribute('id',"toc")
    x.setAttribute('properties',"nav")
    x.setAttribute('href',"TOC.xhtml")
    x.setAttribute('media-type',"application/xhtml+xml")
    manifest.appendChild(x)

    ## Ensure retrocompatibility by also providing a TOC.ncx file
    x = doc.createElement('item')
    x.setAttribute('id',"ncx")
    x.setAttribute('href',"toc.ncx")
    x.setAttribute('media-type',"application/x-dtbncx+xml")
    manifest.appendChild(x)

    x = doc.createElement('item')
    x.setAttribute('id',"titlepage")
    x.setAttribute('href',"titlepage.xhtml")
    x.setAttribute('media-type',"application/xhtml+xml")
    manifest.appendChild(x)

    for i,md_filename in enumerate(md_filenames):
        x = doc.createElement('item')
        x.setAttribute('id',"s{:05d}".format(i))
        x.setAttribute('href',"s{:05d}-{}.xhtml".format(i,md_filename.split(".")[0]))
        x.setAttribute('media-type',"application/xhtml+xml")
        manifest.appendChild(x)

    for i,image_filename in enumerate(image_filenames):
        x = doc.createElement('item')
        x.setAttribute('id',"image-{:05d}".format(i))
        x.setAttribute('href',"images/{}".format(image_filename))
        if "gif" in image_filename:
            x.setAttribute('media-type',"image/gif")
        elif "jpg" in image_filename:
            x.setAttribute('media-type',"image/jpeg")
        elif "jpeg" in image_filename:
            x.setAttribute('media-type',"image/jpg")
        elif "png" in image_filename:
            x.setAttribute('media-type',"image/png")
        if image_filename==description_data["cover_image"]:
            x.setAttribute('properties',"cover-image")

            ## Ensure compatibility by also providing a meta tag in the metadata
            y = doc.createElement('meta')
            y.setAttribute('name',"cover")
            y.setAttribute('content',"image-{:05d}".format(i))
            metadata.appendChild(y)
        manifest.appendChild(x)

    for i,css_filename in enumerate(css_filenames):
        x = doc.createElement('item')
        x.setAttribute('id',"css-{:05d}".format(i))
        x.setAttribute('href',"css/{}".format(css_filename))
        x.setAttribute('media-type',"text/css")
        manifest.appendChild(x)

    ## Now building the spine

    spine = doc.createElement('spine')
    spine.setAttribute('toc', "ncx")

    x = doc.createElement('itemref')
    x.setAttribute('idref',"titlepage")
    x.setAttribute('linear',"yes")
    spine.appendChild(x)
    for i,md_filename in enumerate(md_filenames):
        x = doc.createElement('itemref')
        x.setAttribute('idref',"s{:05d}".format(i))
        x.setAttribute('linear',"yes")
        spine.appendChild(x)

    guide = doc.createElement('guide')
    x = doc.createElement('reference')
    x.setAttribute('type',"cover")
    x.setAttribute('title',"Cover image")
    x.setAttribute('href',"titlepage.xhtml")
    guide.appendChild(x)


    package.appendChild(metadata)
    package.appendChild(manifest)
    package.appendChild(spine)
    package.appendChild(guide)
    doc.appendChild(package)

    return doc.toprettyxml()


def get_container_XML():
    container_data = """<?xml version="1.0" encoding="UTF-8" ?>\n"""
    container_data += """<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n"""
    container_data += """<rootfiles>\n"""
    container_data += """<rootfile full-path="OPS/package.opf" media-type="application/oebps-package+xml"/>\n"""
    container_data += """</rootfiles>\n</container>"""
    return container_data


def get_coverpage_XML(cover_image_path):
    ## Returns the XML data for the coverpage.xhtml file
    all_xhtml = """<?xml version="1.0" encoding="utf-8"?>\n"""
    all_xhtml += """<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="fr">\n"""
    all_xhtml += """<head>\n</head>\n<body>\n"""
    all_xhtml += """<img src="images/{}" style="height:100%;max-width:100%;"/>\n""".format(cover_image_path)
    all_xhtml += """</body>\n</html>"""
    return all_xhtml

def get_TOC_XML(default_css_filenames):
    ## Returns the XML data for the TOC.xhtml file
    toc_xhtml = """<?xml version="1.0" encoding="UTF-8"?>\n"""
    toc_xhtml += """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">\n"""
    toc_xhtml += """<head>\n<meta http-equiv="default-style" content="text/html; charset=utf-8"/>\n"""
    toc_xhtml += """<title>Contents</title>\n"""
    for css_filename in default_css_filenames:
        toc_xhtml += """<link rel="stylesheet" href="css/{}" type="text/css"/>\n""".format(css_filename)
    toc_xhtml += """</head>\n<body>\n"""
    toc_xhtml += """<nav epub:type="toc" role="doc-toc" id="toc">\n<h2>Contents</h2>\n<ol epub:type="list">"""
    ## Add link to cover
    toc_xhtml += """\n<li><a href="titlepage.xhtml">Cover.</a></li>"""
    ## Add link to other sections
    for i,entry in enumerate(get_TOC_dict()["entries"]):
        xhtml = entry["xhtml"]
        full_title = ". ".join(entry["titles"]) + "."
        for subtitle in entry["subtitles"]:
            full_title += """ {}.""".format(titlecase(subtitle.lower()))
        toc_xhtml += """\n<li><a href="{}">{}</a></li>""".format(xhtml,full_title)
    toc_xhtml += """</ol>\n</nav>\n</body>\n</html>"""
    return toc_xhtml

def get_TOCNCX_XML():
    ## Returns the XML data for the TOC.ncx file
    toc_ncx = """<?xml version="1.0" encoding="UTF-8"?>\n"""
    toc_ncx += """<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" xml:lang="fr" version="2005-1">\n"""
    toc_ncx += """<head>\n</head>\n"""
    toc_ncx += """<navMap>\n"""
    ## Add link to cover
    toc_ncx += """<navPoint id="navpoint-cover">\n"""
    toc_ncx += """<navLabel>\n<text>Cover.</text>\n</navLabel>"""
    toc_ncx += """<content src="titlepage.xhtml"/>"""
    toc_ncx += """ </navPoint>"""
    ## Add link to other sections
    for i,entry in enumerate(get_TOC_dict()["entries"]):
        xhtml = entry["xhtml"]
        full_title = ". ".join(entry["titles"]) + "."
        for subtitle in entry["subtitles"]:
            full_title += """ {}.""".format(titlecase(subtitle.lower()))
        toc_ncx += """<navPoint id="navpoint-{}">\n""".format(i)
        toc_ncx += """<navLabel>\n<text>{}</text>\n</navLabel>""".format(full_title)
        toc_ncx += """<content src="{}"/>""".format(xhtml)
        toc_ncx += """ </navPoint>"""
    toc_ncx += """</navMap>\n</ncx>"""
    return toc_ncx

def get_TOC_dict():
    toc = {}
    entries = []
    toc["entries"] = entries
    for i,md_filename in enumerate(chapter_md_filenames()):
        entry = {}
        entries.append(entry)
        filename, extension = os.path.splitext(md_filename)
        entry["filename"] = filename
        entry["xhtml"] = """s{:05d}-{}.xhtml""".format(i,filename)
        entry["titles"] = []
        entry["subtitles"] = []
        if filename.startswith("CHAPTER"):
            with open(os.path.join(work_dir,md_filename),"r",encoding="utf-8") as f:
                markdown_data = f.read()
                for title in re.findall(r"^#\s+(.*)$", markdown_data, re.MULTILINE):
                    entry["titles"].append(title.strip().rstrip("."))
                for subtitle in re.findall(r"^##\s+(.*)$", markdown_data, re.MULTILINE):
                    entry["subtitles"].append(subtitle.strip().rstrip("."))
        else:
            entry["titles"].append(titlecase(filename.replace("_", " ").lower()))
    return toc

def get_chapter_MD(md_filename):
    with open(os.path.join(work_dir,md_filename),"r",encoding="utf-8") as f:
        markdown_data = f.read()

        ## Auto-populate versioning information
        markdown_data = markdown_data.replace("### LATEST VERSION", "### VERSION " + publish_version)

        ## Remove chapter footer navigation that is there to make it helpful to read the content on Github
        footer_index = markdown_data.find("### ~ ~ ~")
        if footer_index > 0:
          markdown_data = markdown_data[0:footer_index]

        return markdown_data

def get_chapter_TXT(markdown_data):
    all_txt = markdown_data
    all_txt = all_txt.replace("###### ", "                    ")
    all_txt = all_txt.replace("##### ", "                ")
    all_txt = all_txt.replace("#### ", "            ")
    all_txt = all_txt.replace("### ", "        ")
    all_txt = all_txt.replace("## ", "    ")
    all_txt = all_txt.replace("# ", "")
    all_txt = all_txt.replace("> ", "    ")
    return all_txt

def get_chapter_HTML(markdown_data):
    html_text = markdown.markdown(markdown_data,
                                  extensions=["codehilite","tables","fenced_code","footnotes"],
                                  extension_configs={"codehilite":{"guess_lang":False}}
                                  )
    ## Use some HTML elements to style capitals because many ereaders do not support small-caps css
    html_text = (
      html_text
        .replace(
          "<h1>THE PRICE OF R",
          "<h1>" +
              "<big>T</big>HE " +
              "<big>P</big>RICE OF " +
              "<big>R</big>"
           )
        .replace(
          "<h1>THE DOORS OF STONE SPECULATIVE M",
          "<h1>" +
              "<big>T</big>HE " +
              "<big>D</big>OORS OF " +
              "<big>S</big>TONE " +
              "<big>S</big>PECULATIVE " +
              "<big>M</big>"
            )
        .replace(
          "<h1>THE KINGKILLER C",
          "<h1>" +
              "<big>T</big>HE " +
              "<big>K</big>INGKILLRR " +
              "<big>C</big>"
           )
        .replace(
          "<h1>LEGAL D",
          "<h1>" +
              "<big>L</big>EGAL " +
              "<big>D</big>"
           )
        .replace(
          "<h1>TABLE OF C",
          "<h1>" +
              "<big>T</big>ABLE OF " +
              "<big>C</big>"
           )
    )
    html_text = (
        html_text
          .replace(
            "<h2>",
            "<h2 class='chapter_subtitle'>",
          )
    )
    for c in ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
      html_text = (
        html_text
          .replace(
            "<h1> THE PRICE OF R",
            "<h1>" +
              "<big>T</big>HE " +
              "<big>P</big>RICE OF " +
              "<big>R</big>"
          )
          .replace(
            "</h2>\n<p>"+c,
            "</h2>\n<p class='no-indent'><big>"+c+"</big>")
          .replace(
            "</h2>\n<p>\""+c,
            "</h2>\n<p class='no-indent'><big>\""+c+"</big>")
          .replace(
            "</h2>\n<p>“"+c,
            "</h2>\n<p class='no-indent'><big>“"+c+"</big>")
          .replace(
            "<h1>"+c,
            "<h1 class='chapter_title'><big>"+c+"</big>")
      )
    return html_text


def get_chapter_XML(markdown_data,css_filenames):
    ## Returns the XML data for a given markdown chapter file, with the corresponding css chapter files
    html_text = get_chapter_HTML(markdown_data)

    all_xhtml = """<?xml version="1.0" encoding="UTF-8"?>\n"""
    all_xhtml += """<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">\n"""
    all_xhtml += """<head>\n<meta http-equiv="default-style" content="text/html; charset=utf-8"/>\n"""


    for css_filename in css_filenames:
        all_xhtml += """<link rel="stylesheet" href="css/{}" type="text/css"/>\n""".format(css_filename)

    all_xhtml += """</head>\n<body>\n"""
    all_xhtml += html_text
    all_xhtml += """\n</body>\n</html>"""

    return all_xhtml

def get_sitemap_XML():
    ## Returns the XML sitemap data
    all_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">"""
    all_xhtml += """
  <url>
    <loc>{}</loc>
    <lastmod>{}</lastmod>
  </url>""".format(website, publish_date)
    all_xhtml += """
  <url>
    <loc>{}{}/{}.-.V{}.txt</loc>
    <lastmod>{}</lastmod>
  </url>""".format(website, release_dir, output_filename, publish_version, publish_date)
    all_xhtml += """
  <url>
    <loc>{}{}/{}.-.V{}.md.txt</loc>
    <lastmod>{}</lastmod>
  </url>""".format(website, release_dir, output_filename, publish_version, publish_date)
    locs = ["Cover_Page", "Resources"]
    for entry in get_TOC_dict()["entries"]:
        locs.append(entry["filename"])
    for loc in locs:
        epoch_seconds = os.path.getmtime(os.path.join(work_dir, loc + ".md"))
        lastmod = datetime.datetime.fromtimestamp(epoch_seconds).strftime('%Y-%m-%d')
        all_xhtml += """
  <url>
    <loc>{}{}/{}.html</loc>
    <lastmod>{}</lastmod>
  </url>""".format(website, work_dir, loc, lastmod)
    all_xhtml += "\n</urlset>"
    return all_xhtml

def chapter_md_filenames():
    with open(os.path.join(work_dir,"description.json"),"r") as f:
        json_data = json.load(f)
    chapter_md_filenames = []
    for _, chapter in enumerate(json_data["chapters"]):
        chapter_md_filenames.append(chapter["markdown"])
    return chapter_md_filenames

if __name__ == "__main__":
    publish()