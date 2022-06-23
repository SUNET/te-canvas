*Documentation for Canvas admins*

# Installing te-canvas as an LTI tool

1. Go to: Admin > Developer Keys > [+ Developer Key] > [+ LTI Key]
2. Choose method: "Enter URL", and enter:
    - JSON URL: https://te-canvas.sunet.se/lti.json
    - Key Name: te-canvas (or whatever you like)
3. Under "State" click "ON"
4. Copy the Client ID number which is visible in the column "Details". Note that this is the string which is shown above the button "Show Key", *not* the string you get if you click this button.
5. Email the Client ID to the person at Sunet who is helping you set this up. To complete the installation we will also need:
    - URL of your Canvas and TimeEdit instances
    - API key for Canvas
    - Username, password, and SOAP API certificate for TimeEdit
6. Once you have received a reply that the server has been updated with your information you can activate the app. To activate te-canvas on a specific course:
    - Go to Course > Settings > Apps > [View App Configurations] > [+ App]
    - Choose "By Client ID" and paste the Client ID from step 4, click Submit.

# Event template strings

In the UI you will find a tab called "Event Template". In this tab you can configure how calendar events are translated from TimeEdit to Canvas. Each field – Title, Location, and Description – should be set to a string which may contain references to TimeEdit *object types* and their *fields* on the format `${type::field}`.

For example:

```
${activity::name} by ${teacher::firstname} ${teacher::lastname}
```

and a TimeEdit reservation with the objects:

```
activity = { name: 'Lecture' },
teacher = { firstname: 'Ernst', lastname: 'Widerberg' }
```

will create the string *Lecture by Ernst Widerberg*.

If there is no object of the specified type on a particular event, the variable will be substituted by an empty string.

Note that these settings are **global**, i.e. they are shared among all courses in your Canvas instance. In general they should only be changed by the Canvas admin at your institution.
