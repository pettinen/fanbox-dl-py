from setuptools import setup


setup(
    name='fanbox_dl',
    version='0.1.0',
    py_modules=['fanbox_dl'],
    install_requires=[
        'click',
        'requests'
    ],
    entry_points='''
        [console_scripts]
        fanbox-dl=fanbox_dl:main
    '''
)
