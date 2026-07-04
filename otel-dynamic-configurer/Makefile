SERVICE_NAME=otel-dynamic-configurer

VERSION=0.130.1
DOCKER_IMAGE_PATH = akshnevrekar/${SERVICE_NAME}:${VERSION}
DOCKERFILE = Dockerfile

docker: compile
	docker build --file ./${DOCKERFILE} -t ${DOCKER_IMAGE_PATH} .

compile: clean

publish: docker
	docker push ${DOCKER_IMAGE_PATH}

clean: