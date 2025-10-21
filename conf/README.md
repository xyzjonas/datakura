# Configuration

This is the central configuration 'app' for the entire Django project, containing all configuration profiles,
all the routing setup and special view/entrypoint for the VueJS app.

HTML index template for the app is copied over from the frontend/dist folder and updated to use the proper
static paths using the STATIC Django macros and most importantly the CSRF token. Both JS and CSS index file hashes
might need to be updated manually.

```html
{% load static %}
<!doctype html>
<html lang="">
  <head>
    ...
    <meta name="csrf-token" content="{{ csrf_token }}">
    <link rel="stylesheet" crossorigin href="{% static 'index-ByKNRtTr.css' %}">
    <script type="module" crossorigin src="{% static 'index-Hw4lRDIx.js' %}"></script>
  </head>
  <body>
    <div id="app"></div>
  </body>
</html>

```