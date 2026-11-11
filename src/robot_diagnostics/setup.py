from setuptools import find_packages, setup

package_name = 'robot_diagnostics'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
    ],
    install_requires=['setuptools'],
    extras_require={'test': ['pytest']},
    zip_safe=True,
    maintainer='robot_diagnostics maintainers',
    maintainer_email='maintainers@example.com',
    description='Read-only odometry and velocity command monitoring.',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'motion_monitor = robot_diagnostics.motion_monitor:main',
    ]},
)
