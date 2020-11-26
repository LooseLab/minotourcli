A client to upload reads to minoTour
====================================

A command line client for uploading sequencing metrics from Oxford Nanopore Technologies MinKNOW to a LooseLab minoTour
server instance.

MinFQ only supports minknow core 4.X.X as it uses ONT's minknow-api, which is only compatible with said version of MinKNOW.

However, base called data can be uploaded from any version of MinKNOW/Guppy.

**To install -**

.. code-block:: python

    pip install minFQ

**Example Commands**

In the example commands below example parameters are:

    - your_user_key: is the long string found in the profile section of your minoTour account.

    - url_to_your_minotour_server: Probably 127.0.0.1, could be a remote address like minotour.nottingham.ac.uk

    - port_for_your_server: Probably 8000

To monitor both live and fastq data.

.. code-block:: python

    minFQ -k [your_user_key] -w /path/to/your/fastq/files -ip 127.0.0.1 -hn
    [url_to_your_minotour_server] -p [port_for_your_server]

To monitor just live data from minKNOW.

.. code-block:: python

    minFQ -k [your_user_key] -ip 127.0.0.1 -hn [url_to_your_minotour_server]
    -p [port_for_your_server] -nf

To monitor live data and enable limited remote control of minKNOW.

.. code-block:: python

    minFQ -k [your_user_key] -ip 127.0.0.1 -hn [url_to_your_minotour_server]
    -p [port_for_your_server] -nf -rc

To monitor just fastq data.

.. code-block:: python

    minFQ -k [your_user_key] -w /path/to/your/fastq/files -hn [url_to_your_minotour_server]
    -p [port_for_your_server] -nm

To monitor fastq statistics only. (Note you will not be able to run subsequent analysis on the server which requires sequence data).

.. code-block:: python

    minFQ -k [your_user_key] -w /path/to/your/fastq/files -hn [url_to_your_minotour_server]
    -p [port_for_your_server] -nm -s

To start an analysis remotely whilst uploading data. Note reference Id may not be required.

.. code-block:: python

    minFQ -k [your_user_key] -w /path/to/your/fastq/files -hn [url_to_your_minotour_server]
     -p [port_for_your_server] -nm -j [job_id] -r [reference_id]

**minFQ Gui**

We are in the process of rebuilding a minFQ gui. Watch this space.
