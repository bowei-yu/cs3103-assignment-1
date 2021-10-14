# CS3103 Programming Assignment 1 - HTTP/HTTPS Proxy

# Instructions to compile and run proxy
### 1. Install Python 3
### 2. For optimal performance, configure the following settings in Firefox about:config
![](images/connections_config.png)
### 3. Pull the Github repository to a destination local folder
### 4. On the target platforms xcne1.comp.nus.edu.sg and xcne2.comp.nus.edu.sg, run the following command:

### **python3 proxy.py <port> <flag_telemetry> blacklist.txt**

</br>

# Q4 Explanation
***(4pt) While running the telemetry, observe and explain the difference between HTTP/1.0 and HTTP/1.1 A way of configuring Firefox default HTTP version is explained in sec.5.1.***

It is observed from running the telemetry that there are comparatively more telemetry outputs from HTTP/1.0. These telemetry outputs also have smaller object sizes and shorter times taken to fetch.

The reason for such a behaviour is because in a default HTTP/1.0 session, TCP connection is torn down and re-established after each HTTP request and response pair, while persistent pipeling in HTTP/1.1 allows for multiple request/response pairs on the same HTTP connection.
