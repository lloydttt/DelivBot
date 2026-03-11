from setuptools import setup

package_name = 'delivery_robot'
python_module_name = 'delivery_robot_nodes'

setup(
    name=package_name,
    version='0.1.0',
    packages=[python_module_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='student',
    maintainer_email='student@example.com',
    description='Hotel delivery robot simulation with turtlesim.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'hotel_map_node = delivery_robot_nodes.hotel_map_node:main',
            'delivery_manager_node = delivery_robot_nodes.delivery_manager_node:main',
            'path_motion_node = delivery_robot_nodes.path_motion_node:main',
            'status_monitor_node = delivery_robot_nodes.status_monitor_node:main',
        ],
    },
)
