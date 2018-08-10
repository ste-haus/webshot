# webshot

Take a screenshot of a webpage

Build the image:
```
docker build -t arychj/webshot .
```

Take a screenshot:
```
docker run --rm -v ~/webshots:/screenshots arychj/webshot https://gitlab.com 500 500
```
