This repo has been superseded `aioafero <https://github.com/Expl0dingBanana/aioafero>`_.



==============
hubspace-async
==============


    Creates a session to HubSpace and handles authentication


This project was designed to asynchronously connect to the HubSpace API and
retrieve data. The implementation was based on
`jdeath/Hubspace-Homeassistant <https://github.com/jdeath/Hubspace-Homeassistant>`_
but converted to async and cleaned up.

Examples
========
These examples provide sample usage when running from the python
shell. If the code is running within an async loop, gathering the loop
and telling it to run is not required.


Gather all devices from the API
-------------------------------

.. code-block:: python

    import logging

    import hubspace_async
    import asyncio


    # TRACE messages in logs
    hubspace_async.logger.setLevel(logging.HS_TRACE)
    hubspace_async.logger.addHandler(logging.StreamHandler())

    try:
        loop = asyncio.get_event_loop()
    except RunTimeError:
        loop = asyncio.new_event_loop()

    username = "<username>"
    password = "<password>

    async def get_devices(username, password):
        connection = hubspace_async.HubSpaceConnection(username, password)
        return await connection.devices



    loop.run_until_complete(get_devices(username, password))

A sample output would look like

.. code-block:: json

   [{"id": "blah1"}, {"id": "blah2"}]

After running this code, the following attributes will be populated:

  * homes: Dictionary of all homes from the API response
  * rooms: Dictionary of all rooms from the API response
  * devices: Dictionary of all devices from the API response


Updating a devices state
------------------------
In this example we will turn a light on. The request requires the use
of ``functionInstance`` for it to work. However some updates
may not require this field.


.. code-block:: python


   from hubspace_async import connection, HubSpaceState
   import asyncio


   conn = connection.HubSpaceConnection("username", "password")
   state = HubSpaceState(
        functionClass="power",
        functionInstance="light-power",
        value="on",
    )
   child_id = "abc123"
   loop.run_until_complete(conn.set_device_state(child_id, new_states))


CLI Commands
============

A CLI is provided for testing your credentials and connection to hubspace.
For all commands, click needs to be installed. The easiest way to install
click is by using the `cli` extras.

``pip install hubspace-async[cli]``


Testing Auth
------------
To test auth, run the following command:
``python -m hubspace_async.cli --username "<username>" --password "<password>" auth-flow``

If successful, the message "Token has been successfully generated" will be displayed.

Testing Connectivity
--------------------
To test connectivity, run the following command:
``python -m hubspace_async.cli --username "<username>" --password "<password>" auth-flow``

If successful, an account id with several hyphens will appear.
