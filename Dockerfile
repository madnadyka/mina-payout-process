FROM ubuntu:20.04
ENV TZ=Europe
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update
RUN apt-get -y install python3
RUN apt-get -y install python3-pip
RUN apt-get -y install git
COPY requirements.txt .
RUN pip3 install --requirement requirements.txt
RUN mkdir config
RUN mkdir src
WORKDIR /src