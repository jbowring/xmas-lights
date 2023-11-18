FROM alpine:3.10

ARG SSH_HOSTNAME
ARG SSH_USERNAME
ARG SSH_PRIVKEY

RUN apk update
RUN apk add openssh
RUN apk add curl
RUN apk add rsync
RUN curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/bin/cloudflared
RUN chmod +x /usr/bin/cloudflared
RUN mkdir /root/.ssh

RUN echo "Host server" >> /root/.ssh/config
RUN echo "User $SSH_USERNAME" >> /root/.ssh/config
RUN echo "HostName $SSH_HOSTNAME" >> /root/.ssh/config
RUN echo "IdentityFile /root/.ssh/key.pem" >> /root/.ssh/config
RUN echo "ProxyCommand cloudflared access ssh --hostname %h" >> /root/.ssh/config
RUN echo "$SSH_PRIVKEY" > /root/.ssh/key.pem
RUN chmod 600 /root/.ssh/key.pem

RUN ssh -o StrictHostKeyChecking=no -n server
