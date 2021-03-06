import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="unigaz",
    version="0.0.1",
    author="Tom Elliott",
    author_email="tom.elliott@nyu.edu",
    description="Work with multiple digital humanities gazetteers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.10.2",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "aaransia",
        "airtight",
        "beautifulsoup4",
        "cyrtranslit",
        "fasttext-langdetect",
        "feedparser",
        "folium",
        "iso639-lang",
        "jsonpickle",
        "language-tags",
        "lxml",
        "pinyin",
        "py3langid",
        "python-slugify",
        "regex",
        "rich",
        "shapely",
        "textnorm",
        "transliterate",
        "validators",
        "webiquette @ git+https://github.com/paregorios/webiquette.git",
        "wget",
    ],
    python_requires=">=3.10.2",
)
