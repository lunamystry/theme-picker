forked from: https://github.com/drybalka/wal-theme-picker

# theme-picker

A helpful script to pick the best suited predefined themes for `wallust` (https://explosion-mental.codeberg.page/wallust/) based on the colors in the image.

`wallust` is a great tool to generate a color palette from the dominant colors in an image and then apply it system-wide. However, sometimes it generates a palette that is too plane or bland, especially for monochromatic images. Such a color scheme is often less useful for syntax-highlighting compared to hand-picked built-in wallust themes. This is the main motivation for the `theme-picker`.

Under the hood `theme-picker` uses k-means clustering to extract the dominant colors in the image, then compares them with themes in `wallust`, assigns each theme a rating based on a semi-empirical color-distance formula, and outputs the best-scoring themes.

Note, that the notion of "the best" theme is very subjective and relies heavily on the personal taste. Therefore, theme-picker` also proposes an interactive menu to try out the best-scoring themes with an option to revert the changes. There is also a possibility to print out the dominant colors and the palette for visual comparison.

### Dependencies
You will need `uv` (https://docs.astral.sh/uv/guides/scripts/#creating-a-python-script) which will automatically install python packages `numpy` and `pillow`.
The other dependency is `wallust`.

### Usage
```
usage: theme-picker.py [-h] [-n N] [-c C] [-p] [-i] image_path

Tries to pick the best color palette for a given image from a set of hand-picked
syntax-highlighting palettes.

positional arguments:
  image_path

optional arguments:
  -h, --help  show this help message and exit
  -n N        number of themes to print
  -c C        number of dominating colors in image
  -p          print image palette (first column) and n best themes in the default image viewer
  -i          call interactive menu to install one of the suggested themes using wallust
```
For example, `theme-picker -n 5 -c 3 -p -i ~/wallpaper.png` will output the names of the 5 best-scoring themes based on the 3 dominant colors in `wallpaper.png`, display the palettes in the default (xdg) image viewer, and start an interactive menu to apply the themes using `wallust`.

# Related

* wallust
  https://codeberg.org/explosion-mental/wallust/src/branch/master/README.md 
* wallust-themes - built in wallust colorschemes
  https://codeberg.org/explosion-mental/wallust-themes
* wal-theme-picker
  https://github.com/drybalka/wal-theme-picker
