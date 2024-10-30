.. image:: https://img.shields.io/pypi/v/skeleton.svg
   :target: `PyPI link`_

.. image:: https://img.shields.io/pypi/pyversions/skeleton.svg
   :target: `PyPI link`_

.. _PyPI link: https://pypi.org/project/skeleton

.. image:: https://github.com/jaraco/skeleton/workflows/tests/badge.svg
   :target: https://github.com/jaraco/skeleton/actions?query=workflow%3A%22tests%22
   :alt: tests

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Code style: Black

.. .. image:: https://readthedocs.org/projects/skeleton/badge/?version=latest
..    :target: https://skeleton.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/badge/skeleton-2022-informational
   :target: https://blog.jaraco.com/skeleton

Introduction
============

A tool to automate custom events using the Pupil Cloud API and GPT-4o.

Requirements
============
- OpenAI subscription and OpenAI API token: Set up yours using `OpenAI's quick start guide <https://platform.openai.com/docs/quickstart/account-setup>`
- Pupil Cloud API token: Click `here <https://cloud.pupil-labs.com/settings/developer>`__ to obtain yours.

Installation
============

In order to download the package, you can simply run the following command from the terminal:

::

   git clone https://github.com/pupil-labs/automate_custom_events.git

Optional, but highly recommended: Create a virtual environment!

::

      python3.11 -m venv venv
      source venv/bin/activate

Go to the folder directory and install the dependencies

::

   cd your_directory/automate_custom_events
   pip install -e . 

Run it!
========

::

   pl-automate-custom-events  

A GUI will appear prompting you to select recording details and enter your desired prompts. To enter the recording details, click on the top button "Select Recording"

Support
========

For any questions/bugs, reach out to our `Discord server <https://pupil-labs.com/chat/>`__  or send us an email to info@pupil-labs.com. 