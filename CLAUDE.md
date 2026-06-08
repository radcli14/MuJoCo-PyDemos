# MuJoCo-PyDemos - Technical Implementation Guide

This project is a showcase of dynamics simulation models using the [MuJoCo](https://mujoco.readthedocs.io/en/stable/overview.html) solver.
Intent is to be informative about how to construct the MJCF-formatted XML file, which will contain the physical dimensions, mass, and appearance, and the Python script that drives the solver, and exports video and plots.
The content is educational, but assume the audience is well-informed (college or professional).

## Simulation Folder Structure

Assuming you are creating a new model in the folder `newmodel`, there will be a `newmodel.xml` file and a `newmodel_sim.py` file in the same folder. 
The Python code will generate a `newmodel_states.png` file with plots, and a `newmodel_sim.mp4` file with video animation.
A `README.md` file inside the folder will explain the model, and will be rendered on the website.
Optionally, there may be a `newmodel_equations.ipynb` file in which equations of motion are derived symbolically using [SymPy Mechanics](https://docs.sympy.org/latest/explanation/modules/physics/mechanics/index.html).

## XML Guidelines

XML is responsible for defining physical and visible configurations, like dimensions, mass, meshes, color, and texture.

If a comment is required to explain a section of the XML, limit it to a single line - when more detail is required, move the comment into `README.md`.
Don't use comments to explain changes to properties that I request in a prompt, use the comments to explain fundamental physics that would be of interest to a third-party viewer.

## Python Guidelines

Python is responsible for running the MuJoCo simulation, generating and exporting videos and plots.

When possible, try to generalize to use common functions in new model, which can be placed in the top-level folder; for example, there is a `common.py` script that gets called by each new model.
If a section of code requires more than a single line comment to explain its usage, and is key to understanding the physics of the model, move that comment into the `README.md` file.

## Documentation Guideline 

Each `README.md` is intended to be rendered in GitHub pages using `jekyll`.
The header of the `README.md` file will contain the following fields:

| Field         | Description/Notes                                   |
|---------------|-----------------------------------------------------|
| `layout`      | See `/_layouts/`                                    |
| `permalink`   | Should be the same as the folder name               |
| `title`       | Titles generally expand and stylize the folder name |
| `subtitle`    | Short explanation of the model, keep to one line    |
| `description` | Longer explanation of the model, 2-4 sentences      |
| `youtube`     | YouTube video ID, I will provide if I upload one    |
| `date`        | Publish date in `YYYY-MM-DD` format; required when `youtube` is set (populates `uploadDate` in VideoObject schema) |
| `plot_image`  | Generally the `newmodel/newmodel_states.png` file.  |
| `image`       | Can be the plot image, or `maxresdefault.jpg` from YouTube, this renders on home page |
| `tags`        | Generally use three tags, physics-related           |
| `specs`       | Generates a table on the right side, format as list of `- { label: "Parameter name", value: "Numbers or description" }` |
| `source_dir`  | Generally `newmodel`                                 |
| `files`       | Generally `- { label: "MJCF Model", name: "newmodel.xml"}` and `- { label: "Python Script", name: "newmodel_"}`, may also include other files |

Content in the header will render either in a right-hand panel on desktop, or below the main readme content on mobile, where "main" content refers to any markdown-formatted text underneath the header.
Use the main readme content to explain items in the XML or Python script that are non-obvious, or that are unique or novel to the example that is being modeled, with code snippets included if they add value. 
Avoid adding much boilerplate or obvious material to the readme for an individual model, but if it is useful and can be applied to multiple models, consider adding it to the main readme at the top level, the setup file, or other common location.

Include equations where necessary to explain a setup in either the XML or Python, such as how a mass or inertial value is calculated.
Don't include equations if we are not actually implementing them in our code files; for example, if equations are completely internal to MuJoCo, and not surfaced in our scripts, don't include them in the documentation.

Make sure to explain what is happening inside the videos, with an intuitive physical explanation; if equations are indded critical to articulating the physics, you can include them.
Make sure to explain what is included in the plots, but don't be overly elaborate with your explanations unless there is some specific area you want to highlight, especially if it connects to something that is observable in videos.

Any time edits are made in a model, either by Claude or by the human, make sure that the readme is consistent with properties defined in the XML or Python.

Do not wrap sentences in the markdown readme with a carriage return to limit the number of characters on a line.
Make each line in the markdown be one complete sentence, and allow the markdown renderer to handle line wrapping.
