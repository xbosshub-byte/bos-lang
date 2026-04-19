from setuptools import setup

setup(
    name='bos-lang',
    version='1.2.0',
    py_modules=['bos'], # ชื่อไฟล์หลักของเรา (ไม่ต้องใส่นามสกุล .py)
    entry_points={
        'console_scripts': [
            'bos=bos:main', # กำหนดให้คำสั่ง 'bos' ไปเรียกฟังก์ชัน main() ในไฟล์ bos.py
        ],
    },
)

