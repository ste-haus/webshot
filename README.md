# webshot

Take a screenshot of a webpage

Build the image:
```
docker build -t ste-haus/webshot .
```

Take a screenshot:
```
docker run --rm -v `pwd`/gitlab.png:/webshot.png ste-haus/webshot https://gitlab.com 500 500
```
