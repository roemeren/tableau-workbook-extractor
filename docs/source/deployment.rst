Deployment
==========

Application Deployment
-----------------------

The Tableau Workbook Extractor application is deployed in two ways:

1. **As a downloadable executable**: Users can easily download the latest 
executable version of the application from the 
`releases page <https://github.com/roemeren/tableau-workbook-extractor/releases/latest>`_. 
Please note that in order to run the downloaded executable file, 
Graphviz must be installed on your local machine.
:ref:`Graphviz must be installed<install-graphviz>`.

2. **As a deployed Dash application on Render**: This option allows users to 
run the application in a cloud environment without the need for local setup. 
The deployed application can be accessed `on this link <https://tableau-workbook-extractor.onrender.com/>`_. 

Both deployment methods are automated through a **GitHub workflow** that is 
triggered each time a new version tag is pushed to the repository. 
This ensures that the latest updates are consistently available to users.

For the Render app deployment to work, the following steps 
are required:

1. **Create a web app on Render**: First, create the web app on the 
Render platform. After creating the app, you will receive a Service ID.

2. **Generate an API key**: On Render, generate an API key to allow programmatic 
access to your app.

3. **Add these secrets to GitHub**: Add the Render Service ID and API key 
respectively as secrets ``RENDER_SERVICE_ID`` and ``RENDER_API_KEY`` to 
the GitHub repository for use in the workflow file.

4. **(Optional) Use a dedicated environment for production**: A separate 
"production" environment has been created within the GitHub repository settings, 
moving the Render API key and Service ID to this environment 
(instead of storing them as repository secrets). This change enhances 
security and manageability, especially when maintaining multiple environments, 
such as development and staging. By isolating production credentials, 
each environment can be configured independently and more securely, 
facilitating better management and control during development and 
testing phases..

You can view the GitHub workflow file responsible for these deployments 
`here <https://github.com/roemeren/tableau-workbook-extractor/blob/main/.github/workflows/release.yml>`_.

These workflows are automated versions of some of the use cases explained in 
the :doc:`usage` page, specifically the creation of an 
executable file using PyInstaller (see :ref:`Create and Run the Executable File<create-run-exe>`) 
and the creation of a Dockerized Dash app (see :ref:`Running the Dockerized Dash Application<run-docker>`).

Documentation Build Process
----------------------------

The documentation for the Tableau Workbook Extractor is generated and 
deployed through a 
`separate GitHub workflow <https://github.com/roemeren/tableau-workbook
-extractor/blob/main/.github/workflows/build-docs.yml>`_.

This workflow is triggered for every tag push (provided that the application 
has been successfully deployed) to ensure that versioned documentation is 
maintained. Additionally, it is triggered for every commit made to the main 
branch, allowing for documentation updates without the need to publish a new 
release. This setup ensures that users always have access to the most 
current information while still preserving the integrity of versioned 
documentation.

To ensure that the documentation is built and published correctly, an orphan 
``gh-pages`` branch must be available, containing an empty 
``.nojekyll`` file. This file prevents GitHub Pages from processing 
the site with Jekyll.

The published site allows users to switch between tags and the latest version 
(called ``main``), ensuring that all documentation is automatically built and 
readily available.
