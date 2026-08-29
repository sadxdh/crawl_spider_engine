from setuptools import setup, find_packages

setup(
    name='crawl_spider_engine',
    version='1.0',
    packages=find_packages(),
    package_data={'': ['*.cfg', '*.ini', '*.conf']},
    entry_points={'scrapy': ['settings = settings']},
    zip_safe=False,
)
