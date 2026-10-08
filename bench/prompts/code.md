
You can also call the same HubSpot tools from Python, with Bash, in your working directory:

    from hubspot import call
    result = call("search_crm_objects", {"objectType": "COMPANY", "limit": 200, "properties": ["name"]})

call(tool_name, arguments) takes the same arguments as the tool and returns the tool's result as parsed JSON (or text). It raises RuntimeError with the tool's message if the tool reports an error. The same limits apply as for direct tool calls. Scripts can loop over many calls; only what you print comes back to you.
