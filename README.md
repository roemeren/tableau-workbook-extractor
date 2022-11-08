# tableau-workbook-extractor

## Getting started

### Cloning the repo

Open a terminal and execute the following commands:

```
cd C:\path\to\root\
git clone https://git.bdbelux.be/remerencia/tableau-workbook-extractor.git
```

### Replicating the environment

To be sure that the code will work correctly a `requirements.txt` file has been included.

In case Anaconda has been installed the following commands can be executed to replicate the environment:

1. Open Anaconda and open a terminal for example in the `base` environment
2. Create a new conda environment (for example `myenv`) using the following commands:
```
conda create --name myenv python=3.10
conda activate myenv
cd C:\path\to\root\myrepo
pip install -r requirements.txt
```

### Install Graphviz

For creating graphs the `Graphviz` software is used and should be installed from here: https://graphviz.org/.

## Description

Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Sources

- [Document API Python documentation](https://tableau.github.io/document-api-python/): describes how workbook and field information can be extracted
- [Pydot repository](https://github.com/pydot/pydot): methods and attributes in `pydot` package used for visualizing graphs
- [Graphviz documentation](https://graphviz.org/docs/nodes/): node and graph attributes

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

### Known issues

- **Not all dependencies are captured**: it is possible that flagged fields/parameters are still used/useful in the workbook because they are for example used in a dashboard URL action. Deleting it in Tableau won't raise any warnings (surprisingly) but the field removal may cause issues.
- **Not all field captions are captured**: some data source field captions (among other attributes) are missing when using the Tableau Document API while these captions can be located in the workbook's raw XML (within the `<metadata-record>`'s `<caption>` tag). It appears to be related to hidden fields (maybe previously unhidden?) in the data source.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.