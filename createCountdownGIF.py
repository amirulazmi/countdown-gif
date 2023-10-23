import os
import sys
import shutil
import argparse
import subprocess
import multiprocessing

def createSVG(svg_path, text, template):
    # Create the SVG content by replacing {text} in the template
    svg_content = template.format(text=text)

    # Save the SVG content to the file
    with open(svg_path, "w") as svg_file:
        # svg_file.write(svg_content)
        svg_file.write(svg_content)

def convertSVG2PNG(svg_path, png_path, inkscape_path):
    subprocess.run([inkscape_path,
                   "--export-type=png", f"--export-filename={png_path}", svg_path])

def createCountdown(minutes, seconds, zerotime):
    count = minutes * 60 + seconds
    countdown_list = [f"{i // 60:02}:{i % 60:02}" for i in range(count, -1, -1)]
    for _ in range(zerotime-1):
        countdown_list.append('00:00')
    return countdown_list

def createGIF(srcfile, dstfile):
    # ffmpeg -framerate 1 -i "10m\frame_%04d.png" -vf "palettegen=stats_mode=diff" palette.png
    subprocess.run(["ffmpeg", "-loglevel", "warning", "-i", srcfile, "-vf",
                   "palettegen=stats_mode=diff", "palette.png", "-hide_banner"])
    # ffmpeg -framerate 1 -i "10m\frame_%04d.png" -i palette.png -filter_complex "paletteuse" -r 1 10_m.gif
    subprocess.run(["ffmpeg", "-loglevel", "warning", "-framerate", "1", "-i", srcfile, "-i",
                   "palette.png", "-filter_complex", "paletteuse", "-r", "1", "-loop", "0", dstfile, "-hide_banner"])

def clearTemp(directory):
    try:
        shutil.rmtree(directory)
        os.remove("palette.png")
        print(f"The directory at {directory} has been successfully deleted.")
    except OSError as e:
        print(f"Error: {e.filename} - {e.strerror}.")

def createImages(text, temp_file, template, inkscape_path):
    temp_svg = temp_file + ".svg"
    createSVG(temp_svg, text, template)
    convertSVG2PNG(temp_svg, temp_file + ".png", inkscape_path)
    os.remove(temp_svg)

def check_inkscape_installation():
    try:
        result = subprocess.run(['where', 'inkscape'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        print("Command 'where' not found. Make sure you are running on a Windows system.")
        return False

# ----------------------------------------------------
if __name__ == "__main__":
    inkscape_path = "./inkscape/bin/inkscape.exe"
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--filename', '-f', type=str,
                        required=True, help='Usage `--filename image.gif`')
    parser.add_argument('--minutes', '-m', type=int,
                        required=True, help='Usage `--minutes 10`')
    parser.add_argument('--seconds', '-s', type=int,
                        default=0, help='Default is 0. Usage `--seconds 10`')
    parser.add_argument('--delay', '-d', type=int,
                        default=10, help='Default is 10. Usage `--delay 10`')
    parser.add_argument('--template', '-t', type=str,
                        help='Path to svg template. Usage `--template C:\\Image\\template.svg`')
    parser.add_argument('--parallel_processing', '-p', type=int,
                        default=0,help='Default is 0. Usage `--parallel_processing 2`')
    args = parser.parse_args()
    

    print("Checking if inkscape.exe available...")
    if check_inkscape_installation():
        inkscape_path = "inkscape"
    elif os.path.exists(inkscape_path):
        inkscape_path = inkscape_path
    else:
        print("Please make sure you have inkscape installation on PATH,")
        print("or you edit the script, set the variable `inkscape_path` on line 59")
        sys.exit(1)
    
    # set svg template
    if args.template == None:
        template = '''<svg width="580" height="150" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#000" />
        <text x="290" y="140" font-family="Arial Black" font-size="180" fill="#fff" text-anchor="middle">{text}</text>
        </svg>'''
    else:
        with open(args.template, 'r') as file:
            template = file.read()

    # append output filename with .gif if not
    filename = (args.filename + ".gif") if not args.filename.lower().endswith(".gif") else args.filename

    # get working directory
    dir = os.getcwd()

    # set temp directory and output file path
    temp_dir = os.path.join(dir, os.path.splitext(filename)[0] + "_temp")
    output_filepath = os.path.join(dir, filename)

    # create temp if not exist
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    countdown = createCountdown(args.minutes, args.seconds, args.delay)
    pattern = "frame_%04d"

    print("creating images ...")
    if(args.parallel_processing == 0):
        for i in range(len(countdown)):
            createImages(countdown[i], os.path.join(temp_dir, pattern % i), template, inkscape_path)
    else:
        with multiprocessing.Pool(processes=args.parallel_processing) as pool:
            results = []
            for i in range(len(countdown)):
                print(f'task {i+1}')
                result = pool.apply_async(createImages, args=(countdown[i], os.path.join(temp_dir, pattern % i), template, inkscape_path))
                results.append(result)

            # Close the pool
            print("finish task")
            pool.close()

            # Wait for all processes to finish
            for result in results:
                result.get()

    print("creating gif ...")
    createGIF(os.path.join(temp_dir, pattern + ".png"), output_filepath)

    if os.path.exists(output_filepath):
        print("removing temp files ...")
        clearTemp(temp_dir)

    print("done")