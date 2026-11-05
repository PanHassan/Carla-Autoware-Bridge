from setuptools import find_packages, setup

setup(
    name='licznik_jazdy',
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/licznik_jazdy']),
        ('share/licznik_jazdy', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='pawel-8934',
    maintainer_email='pawel-8934@users.noreply.github.com',
    description='Licznik jazdy CARLA/Autoware.',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'predkosc = licznik_jazdy.predkosc:main',
        'licznik = licznik_jazdy.licznik:main',
        'okno = licznik_jazdy.okno:main',
    ]},
)
