#!/bin/bash

# Stop the script if any error occurs
set -e

# Stop tim and timbeta
docker stop tim &
docker stop timbeta &
docker stop timdev &
wait

# Stop plugin containers
docker stop csPlugin &
docker stop showFile &
docker stop ChoicePlug &
docker stop ShortNotePlug &
docker stop MultiChoicePlug &
docker stop GraphVizPlug &
wait

# Remove stopped containers
docker rm tim &
docker rm timbeta &
docker rm timdev &
docker rm csPlugin &
docker rm showFile &
docker rm ChoicePlug &
docker rm ShortNotePlug &
docker rm MultiChoicePlug &
docker rm GraphVizPlug &
wait

# Start csPlugin
docker run --name csPlugin -p 56000:5000 -v /opt/cs:/cs/ -d -t -i cs3 /bin/bash -c 'cd /cs && ./run_cs3 ; /bin/bash'

# Start showFile-plugin
docker run --name showFile -p 55000:5000 -v /home/vesal/svn:/svn/ -d -t -i svn /bin/bash -c 'cd /svn && python3 svn3.py ; /bin/bash'

# Start Haskell plugins
docker run --name ChoicePlug -p 57000:5000 -d -t -i haskellplugins /bin/bash -c 'cd /Choices && ./dist/build/ChoicesPlugin/ChoicesPlugin -p 5000 ; /bin/bash'

docker run --name MultiChoicePlug -p 58000:5000 -d -t -i haskellplugins /bin/bash -c 'cd /Choices && ./dist/build/MultipleChoicesPlugin/MultipleChoicesPlugin -p 5000 ; /bin/bash'

docker run --name ShortNotePlug -p 59000:5000 -d -t -i haskellplugins /bin/bash -c 'cd /Choices && ./dist/build/ShortNotePlugin/ShortNotePlugin -p 5000 ; /bin/bash'

docker run --name GraphVizPlug -p 60000:5000 -d -t -i haskellplugins /bin/bash -c 'cd /Choices && ./dist/build/GraphVizPlugin/GraphVizPlugin -p 5000 ; /bin/bash'

# Start timdev
docker run --name timdev -p 50002:5000 -v /opt/tim-dev/:/service -d -t -i tim /bin/bash -c 'cd /service/timApp && export TIM_SETTINGS=/service/timApp/debugconfig.py && source initenv.sh && python3 launch.py ; /bin/bash'

# Start timbeta
docker run --name timbeta -p 50000:5000 -v /opt/tim-beta/:/service -d -t -i tim /bin/bash -c 'cd /service/timApp && export TIM_SETTINGS=/service/timApp/debugconfig.py && source initenv.sh && python3 launch.py ; /bin/bash'

# Start tim
docker run --name tim -p 50001:5000 -v /opt/tim/:/service -d -t -i tim /bin/bash -c 'cd /service/timApp &&source initenv.py && python3 launch.py ; /bin/bash'
