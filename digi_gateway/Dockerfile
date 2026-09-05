ARG BUILD_FROM
FROM $BUILD_FROM

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
COPY digi_gateway.py /app/digi_gateway.py
COPY run.sh /run.sh
RUN chmod 0755 /run.sh /app/digi_gateway.py
CMD ["/run.sh"]
