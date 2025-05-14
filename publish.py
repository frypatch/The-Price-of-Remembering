import markdown # version 3.1
from titlecase import titlecase # version 2.4
import os
from xml.dom import minidom
import zipfile
import sys
import json
import re
import datetime

## mark2epub

## https://github.com/AlexPof/mark2epub
## mark2epub is a simple Python script for converting Markdown files, images, and css files to a single ePub book.


## global variables

today = datetime.date.today()
publish_date = """{}-{}-{}""".format(
    today.year, 
    str(today.month).zfill(2), 
    str(today.day).zfill(2))
publish_version = """{}.{}.{}""".format(
    today.year-2022, 
    str(today.month).zfill(2), 
    str(today.day).zfill(2))

isbn = "the-price-of-remembering-v" + publish_version
work_dir = "book"
build_dir = "published_versions"
output_filename = """The.Price.of.Remembering.-.The.Kingkiller.Chronicle.-.Day.Three.-.V{}""".format(publish_version)
output_md = output_filename + ".md"
output_txt = output_filename + ".txt"
output_epub = output_filename + ".epub"
github_pages_index_html = "index.html"

def get_all_filenames(the_dir,extensions=[]):
    all_files = [x for x in os.listdir(the_dir)]
    all_files = [x for x in all_files if x.split(".")[-1] in extensions]

    return all_files


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
    for i,md_filename in enumerate(all_md_filenames):
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

def get_TOC_XML(default_css_filenames,markdown_filenames):
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
    for i,entry in enumerate(get_TOC_dict(markdown_filenames)["entries"]):
        xhtml = entry["xhtml"]
        full_title = ". ".join(entry["titles"]) + "."
        for subtitle in entry["subtitles"]:
            full_title += """ {}.""".format(titlecase(subtitle.lower()))
        toc_xhtml += """\n<li><a href="{}">{}</a></li>""".format(xhtml,full_title)
    toc_xhtml += """</ol>\n</nav>\n</body>\n</html>"""

    return toc_xhtml

def get_TOCNCX_XML(markdown_filenames):
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
    for i,entry in enumerate(get_TOC_dict(markdown_filenames)["entries"]):
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

def get_chapter_TOC_MD(markdown_filenames):
    all_md = """# CONTENTS\n"""
    all_md += """\n"""
    all_md += """* [*Cover*](#).\n"""
    for entry in get_TOC_dict(markdown_filenames)["entries"]:
        filename = entry["filename"]
        titles = ". ".join(entry["titles"])
        link = "#" + entry["titles"][0].replace(" ","-").lower()
        if filename.startswith("CHAPTER"):
            all_md += """* [{}]({}).""".format(titles,link)
        else:
            all_md += """* [*{}*]({}).""".format(titles,link)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            all_md += """ {}.""".format(titlecase(subtitle.lower()))
        all_md += """\n"""
    return all_md


def get_chapter_TOC_HTML(markdown_filenames):
    all_md = """# CONTENTS\n"""
    all_md += """\n"""
    all_md += """* [*Cover*](#).\n"""
    for entry in get_TOC_dict(markdown_filenames)["entries"]:
        filename = entry["filename"]
        titles = ". ".join(entry["titles"])
        link = "#" + filename
        if filename.startswith("CHAPTER"):
            all_md += """* [{}]({}).""".format(titles,link)
        else:
            all_md += """* [*{}*]({}).""".format(titles,link)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            all_md += """ {}.""".format(titlecase(subtitle.lower()))
        all_md += """\n"""
    return get_chapter_HTML(all_md)

def get_chapter_TOC_TXT(markdown_filenames):
    all_txt = """CONTENTS.\n"""
    all_txt += """\n\n"""
    for entry in get_TOC_dict(markdown_filenames)["entries"]:
        filename = entry["filename"]
        xhtml = entry["xhtml"]
        titles = ". ".join(entry["titles"])
        all_txt +="""    {}.""".format(titles)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            all_txt += """ {}.""".format(titlecase(subtitle.lower()))
        all_txt += """\n"""
    return all_txt

def get_chapter_TOC_XML(markdown_filenames, css_filenames):
    all_md = """# CONTENTS\n"""
    all_md += """\n"""
    all_md += """* [*Cover*](titlepage.xhtml).\n"""
    for entry in get_TOC_dict(markdown_filenames)["entries"]:
        filename = entry["filename"]
        xhtml = entry["xhtml"]
        titles = ". ".join(entry["titles"])
        if filename.startswith("CHAPTER"):
            all_md += """* [{}]({}).""".format(titles,xhtml)
        else:
            all_md += """* [*{}*]({}).""".format(titles,xhtml)
        subtitles = entry["subtitles"]
        for subtitle in subtitles:
            all_md += """ {}.""".format(titlecase(subtitle.lower()))
        all_md += """\n"""
    return get_chapter_XML(all_md, css_filenames)

def get_TOC_dict(markdown_filenames):
    toc = {}
    entries = []
    toc["entries"] = entries
    for i,md_filename in enumerate(markdown_filenames):
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
            "<h1>"+c,
            "<h1><big>"+c+"</big>")
          .replace(
            "</h2>\n<p>"+c,
            "</h2>\n<p><big>"+c+"</big>")
          .replace(
            "</h2>\n<p>\""+c,
            "</h2>\n<p><big>\""+c+"</big>")
          .replace(
            "</h2>\n<p>“"+c,
            "</h2>\n<p><big>“"+c+"</big>")
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

if __name__ == "__main__":
    
    if not os.path.exists(build_dir):
      os.makedirs(build_dir)

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
    ## Now creating the txt book
    txt_data = ""
    for i,chapter in enumerate(json_data["chapters"]):
        chapter_md_filename = chapter["markdown"]
        if chapter_md_filename == "Contents.md":
            txt_data += get_chapter_TOC_TXT(all_md_filenames)
        else:
            markdown_data = get_chapter_MD(chapter_md_filename)
            txt_data += get_chapter_TXT(markdown_data)
        txt_data += "\n\n\n\n"
    txt_file = open(os.path.join(build_dir, output_txt), "w")
    txt_file.write(txt_data)
    txt_file.close()

    ######################################################
    ## Now creating the md book
    md_page_break = "\n\n\n\n--------------------\n\n\n\n"
    md_data = ""
    md_data += "![The Price of Remembering](book/images/cover.jpg)"
    md_data += md_page_break
    for i,chapter in enumerate(json_data["chapters"]):
        chapter_md_filename = chapter["markdown"]
        if chapter_md_filename == "Contents.md":
            md_data += get_chapter_MD("Downloads.md").strip('\n')
            md_data += md_page_break
            md_data += get_chapter_TOC_MD(all_md_filenames).strip('\n')
        else:
            md_data += get_chapter_MD(chapter_md_filename).strip('\n')
        md_data += md_page_break
    md_file = open(os.path.join(build_dir, output_md), "w")
    md_file.write(md_data)
    md_file.close()

    ######################################################
    ## Now creating the html book
    html_page_anchor_template = """<a name="{}">"""
    html_data = """<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="UTF-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The-Price-of-Remembering</title>
<link rel="stylesheet" href="book/css/general.css">
<link rel="stylesheet" href="book/css/code_styles.css">
<link rel="stylesheet" href="book/css/chapter.css">
</head>
<body>
<img alt="The Price of Remembering Cover" src="book/images/cover.jpg" />
<hr />"""
    for i,chapter in enumerate(json_data["chapters"]):
        chapter_md_filename = chapter["markdown"]
        if chapter_md_filename == "Contents.md":
            html_data += "\n" + html_page_anchor_template.format("downloads")
            html_data += "\n" + get_chapter_HTML(get_chapter_MD("Downloads.md"))
            html_data += "\n<hr />"
            html_data += "\n" + html_page_anchor_template.format("contents")
            html_data += "\n" + get_chapter_TOC_HTML(all_md_filenames)
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
    html_file = open(github_pages_index_html, "w")
    html_file.write(html_data)
    html_file.close()


    ######################################################
    ## Now creating the ePUB book

    with zipfile.ZipFile(os.path.join(build_dir, output_epub), "w" ) as myZipFile:

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
                chapter_data = get_chapter_TOC_XML(all_md_filenames, chapter_css_filenames)
            else:
                markdown_data = get_chapter_MD(chapter_md_filename)
                chapter_data = get_chapter_XML(markdown_data,chapter_css_filenames)
            myZipFile.writestr("OPS/s{:05d}-{}.xhtml".format(i,chapter_md_filename.split(".")[0]),
                               chapter_data.encode('utf-8'),
                               zipfile.ZIP_DEFLATED)


        ## Writing the TOC.xhtml file
        toc_xml_data = get_TOC_XML(json_data["default_css"],all_md_filenames)
        myZipFile.writestr("OPS/TOC.xhtml",toc_xml_data.encode('utf-8'),zipfile.ZIP_DEFLATED)

        ## Writing the TOC.ncx file
        toc_ncx_data = get_TOCNCX_XML(all_md_filenames)
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

    print("INFO: eBook creation complete")
