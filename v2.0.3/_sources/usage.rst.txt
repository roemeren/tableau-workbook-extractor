Usage
=====

This tool can be run in several ways, depending on your needs.

The **recommended and primary option** is to use the **Dash app**,  
available either as a :ref:`deployed version on Render<run-render>` or by :ref:`running it locally<dash-local>`.  
The Dash app replaces the earlier Flask version and provides the same core 
functionality along with additional interactive dashboard features.

For users who prefer alternative setups, legacy and advanced options remain available.  
These include running the :ref:`Python script<run-python>`, 
creating or running a :ref:`standalone executable<create-run-exe>`, 
or using a :ref:`dockerized version of the Dash app<run-docker>`.  
Older options such as the :ref:`Flask app<run-flask>` and CLI tool are still documented 
for reference but are no longer maintained.

.. :hidden: option makes the toctree hidden in the page
.. toctree::
   :maxdepth: 1
   :hidden: 

   output_files

Option 1: Downloading the Executable File (Legacy)
--------------------------------------------------

.. _download-run-exe:

Prerequisite 1: Install Graphviz
""""""""""""""""""""""""""""""""

.. _install-graphviz:

To install Graphviz on Windows, download the latest installer from the 
official `Graphviz download page <https://graphviz.org/download/>`_ and run it, 
following the on-screen instructions.

During installation, make sure that the  **add Graphviz to the PATH variable**
is checked (this is unchecked by default). This way it can be accessed from 
the command line.

.. image:: _static/images/02-graphviz-installation.png
   :alt: Graphviz Installation PATH Variable
   :width: 350

To verify the installation, open a Command Prompt and type ``dot -V`` 
to check the version.

.. warning::

    **Some versions may be blocked** by Microsoft Defender Smartscreen:

    .. image:: _static/images/01-microsoft-defender.png
       :alt: Microsoft Defender Smartscreen
       :width: 350
    
    This can be bypassed by **right-clicking** on the file and clicking on **Properties**. 
    Next, the **Unblock** option should be checked after which the executable can be run.

    .. image:: _static/images/08-unblock-exe.png
       :alt: Unblock Blocked Executable
       :width: 350

    An alternative method is to run the exe using the **Command Prompt**: 
    change the directory to the file's download location and then Run the 
    executable with the command ``my-executable`` or  ``my-executable.exe``.

Step 1: Download and Run the Executable File
""""""""""""""""""""""""""""""""""""""""""""

Download the executable version of the Python script ``cli_main.py`` 
from the `GitHub Releases page <https://github.com/roemeren/tableau-workbook-extractor/releases>`_:

.. image:: _static/images/03-releases.png
   :alt: Download Release Executable
   :width: 350

Double-clicking on the executable will launch the tool which consists of the 
following steps:

First, the user needs to browse to a local Tableau workbook (``.twb`` or ``.twbx`` file):

.. image:: _static/images/04-browse-file.png
    :alt: Browse Tableau Workbook easygui
    :width: 700

Once the file is selected it will be processed, and progress can be tracked 
through printed log lines and/or progress bars.

If everything runs as expected the user is prompted to ``press Enter to exit`` the program:

.. image:: _static/images/07-exit.png
    :alt: Command Prompt Exit Message Success
    :width: 700

In case something goes the error is printed out after which the user is also 
prompted to press Enter to exit.

.. image:: _static/images/08-error.png
    :alt: Command Prompt Exit Message Error
    :width: 700

Upon completion, the output files will be stored in a newly created folder 
named ``<my workbook> Files`` within the same directory as the selected workbook:

.. image:: _static/images/05-output-file.png
    :alt: Local Output File Storage
    :width: 500

.. note::
    
    The main **advantage** of the executable is that it is fast and 
    straightforward, allowing users to run the tool without the need to 
    clone the repository or set up a Python environment first.

    The main **drawback** is that Graphviz must be installed separately 
    and configured correctly for the executable to function properly.

Option 2: Accessing the Application on Render (**Recommended**)
---------------------------------------------------------------

.. _run-render:

A `Dash <https://dash.plotly.com/>`_ app version of the tool has 
been dockerized and deployed as a 
web application using `Render <https://render.com/>`_, accessible at 
https://tableau-workbook-extractor.onrender.com/.

Running the Dash application is an alternative way to use the 
tool, offering similar functionality to running an executable:

- First, the user needs to either select one of the sample workbooks or 
  upload a local Tableau workbook (``.twb`` or ``.twbx`` file) using a browse 
  button in the app
- Once the file is selected a button can be clicked to execute the processing.
  Progress is tracked and checked through the web interface and an output log 
  file instead of printed logs on the command line.
- Upon completion, the generated output are zipped which can be downloaded 
  by the user (see image below).

.. image:: _static/images/24-usage-dash.png
    :alt: Dash Output Download Button
    :width: 350

By default, the application generates only SVG dependency graphs, but users can 
optionally enable PNG generation through a checkbox on the upload page before 
starting the processing.

.. note::

    The main **advantage** of this web app compared to running the executable is that 
    it eliminates the need for users to install Graphviz separately, as Docker 
    is used to package and deploy the entire application along with all its 
    dependencies, including the Python version and required packages.

    The main **drawback** is that the app is hosted on the free tier of Render, 
    which can result in longer loading times as the Docker container 
    needs to be started up first.

Option 3: Executing the Python Script in the Command Line (Legacy)
------------------------------------------------------------------

.. _run-python:

This section explains how to run the Python script ``cli_main.py`` directly on 
your local machine, bypassing the need for the executable. 
Running the script locally provides more flexibility, allowing you to 
customize the code, use virtual environments, or troubleshoot in real-time.

However, to ensure the tool runs properly, you will need to install both Git 
and Graphviz.

Prerequisite 1: Install Git
"""""""""""""""""""""""""""

.. _install-git:

To install Git on Windows, download the installer 
from the official `Git for Windows site <https://git-scm.com/>`_ 
and follow the setup wizard to complete the installation. 

After installation, open Git Bash and verify the installation by typing
 ``git --version``, allowing you to clone repositories from GitHub and 
 other sources.

Prerequisite 2: Install Graphviz
"""""""""""""""""""""""""""""""""

For instructions on how to install Graphviz, see :ref:`Install Graphviz<install-graphviz>`

Step 1: Clone the Repository
"""""""""""""""""""""""""""""

.. _clone-repo:

You need to clone a Git repository to create a local copy of the project on your computer.

To do this, open a new PowerShell terminal and set the working directory 
to the directory where you'll clone the ``tableau-workbook-extractor`` 
git repository. For example:

.. code-block:: console

   $ cd C:\Users\jdoe\Documents\Repositories\

The repository can then be cloned (using HTTPS) by running this command:

.. code-block:: console

   $ git clone https://github.com/roemeren/tableau-workbook-extractor.git

Step 2: Create an Environment
"""""""""""""""""""""""""""""

.. _create-env:

Creating a virtual environment ensures that the project dependencies are 
isolated from other projects on your system, preventing conflicts. 

Installing dependencies from a ``requirements.txt`` file guarantees that 
you have all the necessary packages and their correct versions needed 
for the project to run properly.

To do this, set the working directory to the cloned repository from the 
previous step, for example:

.. code-block:: console

   $ cd tableau-workbook-extractor

Next, run the following commands to create and activate the virtual environment:

.. code-block:: console

   $ python -m venv .venv
   $ .venv\Scripts\activate.bat

.. note::

   If using PowerShell, the commands are slightly different. It may also be 
   needed to temporarily override PowerShell's Execution Policy to allow 
   scripts to run in the current session:

   .. code-block:: console

      $ python -m venv .venv
      $ Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
      $ .venv\Scripts\Activate.ps1

Finally, the dependencies from the provided ``requirements.txt`` file (located 
inside the ``app`` subfolder) can be installed using ``pip``:

.. code-block:: console

   $ pip install -r app/requirements.txt

Step 3: Execute the Python Script
"""""""""""""""""""""""""""""""""

To run the application, set the working directory to the repo's ``app`` 
subfolder. For example:

.. code-block:: console

   $ cd C:\Users\jdoe\Documents\Repositories\tableau-workbook-extractor\app

In case you are already inside the repo's root directory it suffice to run 
the command ``cd app``.

Inside this folder the main script ``cli_main.py`` will prompt the user 
to browse to a local ``.twb`` or ``.twbx`` file, after which the processing 
progress is displayed through printed log lines and progress bars for certain steps.

To execute the script:

.. code-block:: console

   $ python cli_main.py

Option 4: Create and Run the Executable File (Legacy)
------------------------------------------------------

.. _create-run-exe:

Creating an executable with ``PyInstaller`` allows you to package your Python 
tool into a standalone application that can be run without requiring a 
Python environment or external dependencies on the user's machine. 

This option is useful if you want to customize the build, add specific 
configurations, or distribute the tool internally without relying on 
downloading pre-built releases from GitHub. 

The general workflow involves first setting up a Python environment with 
all the necessary dependencies, including ``PyInstaller`` (already included in 
the repo's ``requirements.txt`` file). Next, you run PyInstaller to 
package the tool into an executable, which can be run, shared or distributed 
without requiring a separate Python installation.

Prerequisites: Install Git and Graphviz
""""""""""""""""""""""""""""""""""""""""

For instructions on how to install Git and Graphviz, see resp. 
:ref:`Install Git<install-git>` and :ref:`Install Graphviz<install-graphviz>`.

Step 1: Clone the Repository and Create an Environment
"""""""""""""""""""""""""""""""""""""""""""""""""""""""

For instructions on how to clone the repository and create the Python 
environment, see resp. 
:ref:`Clone the Repo<clone-repo>` and :ref:`Create an Environment<create-env>`.

Step 2: Create the Executable File
"""""""""""""""""""""""""""""""""""

To create the executable file, set the working directory to the repo's root 
folder. For example:

.. code-block:: console

   $ cd C:\Users\jdoe\Documents\Repositories\tableau-workbook-extractor

The following command will create the executable based on the application's 
``cli_main.py`` script inside the repo's subfolder ``dist``:

.. code-block:: console

   $ pyinstaller --onefile app/cli_main.py

The resulting ``dist\cli_main.exe`` executable can be moved if needed and run by 
double-clicking it, allowing you to browse to a file and view progress and 
logs directly in the command line window.

Option 5: Running the Flask Application (Legacy)
-------------------------------------------------

.. _run-flask:

In this section, you'll find instructions on how to run the Flask app version 
of the tool locally on your machine. 

This provides the same functionality as the web version, allowing you to 
upload Tableau workbooks, process them, and download the results—without 
relying on an external deployment like Render.

Prerequisites: Install Git and Graphviz
""""""""""""""""""""""""""""""""""""""""

For instructions on how to install Git Graphviz, see resp. 
:ref:`Install Git<install-git>` and :ref:`Install Graphviz<install-graphviz>`.

Step 1: Clone the Repository and Create an Environment
"""""""""""""""""""""""""""""""""""""""""""""""""""""""

See resp. :ref:`Clone the Repository<clone-repo>` and 
:ref:`Create an environment<create-env>`.

Step 2: Run the App
"""""""""""""""""""

.. _flask-local:

To run the application, set the working directory to the repo's ``app`` 
subfolder. For example:

.. code-block:: console

   $ cd C:\Users\jdoe\Documents\Repositories\tableau-workbook-extractor\app

In case you are already inside the repo's root directory it suffice to run 
the command ``cd app``.

Inside this folder the main script ``web\flask_app.py`` will start the 
application that will typically be available on ``localhost:5000`` (to be 
verified in the Command Prompt, check for example for
``Running on http://127.0.0.1:5000``).

To execute the script (run as a module to ):

.. code-block:: console

   $ python -m web.flask_app

.. note::

    To maintain proper relative imports, like ``import shared.common`` 
    (referring to the ``shared\common.py`` script inside the ``app`` folder), 
    the Flask app needs to be run as a module from the root directory as 
    shown in the code block above, not as a script

Option 6: Running the Dash Application (**Recommended**)
---------------------------------------------------------

.. _dash-local:

The Dash app is the recommended version to run locally, as it replaces the 
earlier Flask interface and provides a more complete, interactive experience 
with additional features such as workbook statistics, dependency graphs, and 
field-level exploration.

Running the Dash app locally is nearly identical to running the Flask app.  
The only difference is the Python file that needs to be executed.

To start the app, navigate to the repo's ``app`` subfolder:

.. code-block:: console

   $ cd C:\Users\jdoe\Documents\Repositories\tableau-workbook-extractor\app

Then run the Dash application module:

.. code-block:: console

   $ python -m web.dash_app

The dashboard will typically be available at ``http://127.0.0.1:8050``.

.. note::

   The Dash app supersedes the earlier Flask version, which is no longer 
   expanded or maintained. It is therefore recommended to use the Dash app 
   for all new analyses.

Option 7: Running the Dockerized Dash Application
-------------------------------------------------

.. _run-docker:

This section explains how to run a dockerized version of the Dash app locally, 
providing an alternative to using the deployed version on Render.  
Running the tool locally in Docker ensures that all dependencies, 
including Graphviz, are preconfigured and removes the wait time associated 
with the free-tier deployment on Render.

Compared to the earlier Flask version, the Dash app offers a richer, 
interactive dashboard with workbook statistics, dependency graphs, and 
field-level exploration. It is the **recommended version** to use going forward.

Prerequisite: Install Docker
""""""""""""""""""""""""""""

To install Docker on Windows, visit the official  
`Docker Desktop for Windows <https://www.docker.com/products/docker-desktop/>`_  
page and follow the installation instructions.

Step 1: Build the Image
""""""""""""""""""""""""

The ``app`` folder of the repository contains a ``Dockerfile`` that defines how 
to build the image, including all dependencies and exposed ports 
(in this case **8050**). 

Set the working directory to the repo's ``app`` subfolder. For example:

.. code-block:: console

   $ cd C:\Users\jdoe\Documents\Repositories\tableau-workbook-extractor\app

If you are already inside the repo's root directory, it suffices to run 
``cd app``.

Next, build the Docker image (named ``tableau-workbook-extractor``)  
by running the following command (ensure that Docker Desktop is running):

.. code-block:: console

   $ docker build -t tableau-workbook-extractor .

Step 2: Run the Container
""""""""""""""""""""""""""

Once the image is built, start a container from it using:

.. code-block:: console

   $ docker run -p 8050:8050 tableau-workbook-extractor

Similar to :ref:`running the Dash app locally<dash-local>`,  
the dashboard will be accessible in your browser at ``http://localhost:8050``.
