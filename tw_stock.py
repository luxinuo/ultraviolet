import subprocess


input_start = input('Type the start date: ')
input_end = input('Type the end date: ')


if input_start and input_end:
	subprocess.run(f'python3 src/utils/twse_crawler.py {input_start} {input_end}', shell=True)
