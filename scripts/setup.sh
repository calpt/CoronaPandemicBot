#!/bin/bash
cd $( dirname "${BASH_SOURCE[0]}" )
chmod 755 init/coronapandemicbot
cp init/* /etc/init.d
sudo update-rc.d coronapandemicbot defaults
