# webshot

Take a screenshot of a webpage

Build the image:
```
docker build -t arychj/webshot .
```

Take a screenshot:
```
docker run --rm -v `pwd`/gitlab.png:/webshot.png arychj/webshot https://gitlab.com 500 500
```
