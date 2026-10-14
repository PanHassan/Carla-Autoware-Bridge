from glob import glob

from setuptools import setup

package_name = 'carla_autoware_examples'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.xml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    description='Przykładowe węzły ROS 2 do pracy z Autoware i CARLA',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'speed_monitor = carla_autoware_examples.speed_monitor:main',
            'drive_to_goal = carla_autoware_examples.drive_to_goal:main',
        ],
    },
)
