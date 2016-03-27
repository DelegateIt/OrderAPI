#!/usr/bin/env python3

import sys
REQUIRED_PYTHON = (3, 4, 0)
if sys.version_info < REQUIRED_PYTHON:
    print("Please upgrade your version of python to at least v{}.{}.{}".format(*REQUIRED_PYTHON))
    exit(1)

# Set the scripts working directory to it's own location so relative
# paths work as expected
import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

import argparse
import subprocess
import tempfile
import json

def execute_no_fail(command, *args, **kwargs):
    result = execute(command, *args, **kwargs)
    if result[0] != 0:
        raise Exception("The command {} returned {}".format(command, result[0]))
    return result

def execute(command, cwd=None, shell=False, stdout=None, stderr=None):
    print("EXECUTING:", " ".join(command))
    # return 0, "".encode("utf-8"), "".encode("utf-8")
    proc = subprocess.Popen(command, cwd=cwd, shell=shell, stdout=stdout, stderr=stderr)
    (out, err) = proc.communicate()
    return proc.wait(), out, err

class Git(object):

    @staticmethod
    def ensure_updated_head(repopath="."):
        print("Ensuring there are no un-pushed changes")
        execute_no_fail(["git", "diff", "--exit-code", "--stat", "origin/master"], cwd=repopath)

    @staticmethod
    def get_latest_commit_hash(repopath="."):
        binary = execute_no_fail(["git", "rev-parse", "HEAD"], cwd=repopath, stdout=subprocess.PIPE)[1]
        return binary.decode("utf-8").strip("\n")


class Start(object):
    @staticmethod
    def start_all():
        for name in ["db", "api", "ntfy"]:
            print("Starting", name, "container")
            execute_no_fail(["docker", "start", name])
        print("\nThe api is accessible from port 8000 and socket.io from 8060")

    @staticmethod
    def setup_all():
        volume_overrides = { "apisource": os.getcwd() }
        with open("./docker/api/Dockerrun.aws.json", "r") as f:
            Create.setup_with_dockerrun(json.loads(f.read()), True, volume_overrides, "host")
        with open("./docker/notify/Dockerrun.aws.json", "r") as f:
            Create.setup_with_dockerrun(json.loads(f.read()), True, volume_overrides, "host")
        with open("./docker/db/Dockerrun.aws.json", "r") as f:
            Create.setup_with_dockerrun(json.loads(f.read()), True, volume_overrides, "host")

    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(description="Starts the api environment")
        parser.add_argument("-l", "--local", default=False, action="store_true",
                help="Don't pull any images, just run the latest local tag")
        args = parser.parse_args()
        if not args.local:
            Start.setup_all()
        Start.start_all()

class Stop(object):
    @staticmethod
    def stop_container(name, time_till_kill=3):
        print("Stopping {} container".format(name))
        return execute_no_fail(["docker", "stop", "-t", str(time_till_kill), name])

    @staticmethod
    def stop_api_env():
        Stop.stop_container("ntfy")
        Stop.stop_container("api")
        Stop.stop_container("db")

    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(description="Stops the api environment")
        parser.parse_args()
        Stop.stop_api_env()


class Create(object):
    @staticmethod
    def kill_and_delete(name):
       execute(["docker", "rm", "-f", name])

    @staticmethod
    def create_image(name, source, no_cache):
        args = ["docker", "build", "-t", name]
        if no_cache:
            args.append("--no-cache")
        args.append(source)
        execute_no_fail(args)

    @staticmethod
    def pull_image(name):
        execute_no_fail(["docker", "pull", name])

    @staticmethod
    def setup_with_dockerrun(dockerrun, port_mirror=False, volume_overrides={}, net="bridge"):
        containers = dockerrun["containerDefinitions"]
        volume_mounts = {
                v["name"]: volume_overrides.get(v["name"], v["host"]["sourcePath"])
                for v in dockerrun["volumes"] }
        for c in containers:
            ports = [
                    [ p["containerPort"] if port_mirror else p["hostPort"], p["containerPort"] ]
                    for p in c["portMappings"] ]
            volumes = [
                    [ volume_mounts[v["sourceVolume"]], v["containerPath"] ]
                    for v in c["mountPoints"] ]
            Create.pull_image(c["image"])
            Create.kill_and_delete(c["name"])
            Create.create_container(c["name"], c["image"], ports=ports, volumes=volumes, net=net)

    @staticmethod
    def create_container(name, image, ports=None, volumes=None, links=None, tty=False, net="bridge"):
        command = ["docker", "create", "--name", name]
        if ports:
            for p in ports:
                command.extend(["-p", str(p[0]) + ":" + str(p[1])])
        if volumes:
            for v in volumes:
                command.extend(["-v", v[0] + ":" + v[1]])
        if links:
            for link in links:
                command.extend(["--link", link])
        if tty:
            command.append("-t")
        command.append("--net=" + net)
        command.append(image)
        execute(command)

    @staticmethod
    def setup_api_container(volume, no_cache):
        Create.kill_and_delete("api")
        Create.create_image("delegateit/gatapi", "./docker/api", no_cache)
        Create.create_container("api", "delegateit/gatapi",
                ports=[[8000, 8000]],
                volumes=[[volume, "/var/gator/api"]],
                net="host")

    @staticmethod
    def setup_ntfy_container(volume, no_cache):
        Create.kill_and_delete("ntfy")
        Create.create_image("delegateit/gatntfy", "./docker/notify", no_cache)
        Create.create_container("ntfy", "delegateit/gatntfy",
                ports=[[8060, 8060]],
                volumes=[[volume, "/var/gator/api"]],
                net="host")

    @staticmethod
    def setup_db_container(volume, no_cache):
        Create.kill_and_delete("db")
        Create.create_image("delegateit/gatdb", "./docker/db", no_cache)
        Create.create_container("db", "delegateit/gatdb",
                ports=[[8040, 8040]],
                volumes=[[volume, "/var/gator/api"]],
                net="host")
    @staticmethod
    def parse_args():
        containers = ["api", "db", "ntfy", "fullapi"]
        parser = argparse.ArgumentParser(description="docker container and image creation for DelegateIt")
        parser.add_argument("name", choices=containers,
                help="the name of the container to create.")
        parser.add_argument("--no-cache", default=False, action="store_true", dest="no_cache",
                help="Do not use docker's cache when building images.")
        args = parser.parse_args()

        abs_source = os.getcwd()
        Create.create_image("delegateit/gatbase", "./docker/base", args.no_cache)
        if args.name == "api" or args.name == "fullapi":
            Create.setup_api_container(abs_source, False)
        if args.name == "db" or args.name == "fullapi":
            Create.setup_db_container(abs_source, False)
        if args.name == "ntfy" or args.name == "fullapi":
            Create.setup_ntfy_container(abs_source, False)

class Package(object):
    excludes = [
        "*/.git/*",
        "*/__pycache__/*",
        "*/.elasticbeanstalk/*",
        "*.swp",
        "*/.noseids",
        "apisource/testlib/*"
    ]

    @staticmethod
    def package_lambda(apisource, apiconfig, outdir, tempdir):
        print("Packaging lambda")
        execute(["rm", os.path.join(outdir, "gator-lambda.zip")])
        execute_no_fail(["cp", "-R", os.path.join(apisource, "notify"), tempdir])
        execute_no_fail(["cp", apiconfig, os.path.join(tempdir, "notify", "config.json")])
        execute_no_fail(["zip", "-r", os.path.join(os.getcwd(), outdir, "gator-lambda.zip"),
                "lambda.js",
                "gator.js",
                "push_notifications.py",
                "config.json"],
                cwd=os.path.join(tempdir, "notify"))

    @staticmethod
    def package_api(apisource, apiconfig, outdir, tempdir):
        print("Packaging api")
        execute(["rm", os.path.join(outdir, "gator-api.zip")])
        execute_no_fail(["cp", "-R", apisource, os.path.join(tempdir, "apisource")])
        execute_no_fail(["cp", apiconfig,
                os.path.join(tempdir, "apisource", "local-config.json")])
        execute_no_fail(["cp", os.path.join("docker", "api", "Dockerrun.aws.json"), tempdir])
        execute_no_fail(["cp", os.path.join("docker", "api", "env.yaml"), tempdir])
        zip_args = ["zip", "-r", os.path.join(os.getcwd(), outdir, "gator-api.zip"),
                "apisource",
                "Dockerrun.aws.json",
                "env.yaml",
                "-x"]
        zip_args.extend(Package.excludes)
        execute_no_fail(zip_args, cwd=tempdir)

    @staticmethod
    def package_notify(apisource, apiconfig, outdir, tempdir):
        print("Packaging notify")
        execute(["rm", os.path.join(outdir, "gator-notify.zip")])
        execute_no_fail(["cp", "-R", apisource, os.path.join(tempdir, "apisource")])
        execute_no_fail(["cp", apiconfig,
                os.path.join(tempdir, "apisource", "local-config.json")])
        execute_no_fail(["cp", os.path.join("docker", "notify", "Dockerrun.aws.json"), tempdir])
        execute_no_fail(["cp", os.path.join("docker", "notify", "env.yaml"), tempdir])
        zip_args = ["zip", "-r", os.path.join(os.getcwd(), outdir, "gator-notify.zip"),
                "apisource",
                "Dockerrun.aws.json",
                "env.yaml",
                "-x"]
        zip_args.extend(Package.excludes)
        execute_no_fail(zip_args, cwd=tempdir)

    @staticmethod
    def package_all(apisource, apiconfig, outdir):
        with tempfile.TemporaryDirectory() as tempdir:
            api_temp = os.path.join(tempdir, "api")
            notify_temp = os.path.join(tempdir, "notify")
            lambda_temp = os.path.join(tempdir, "lambda")
            execute_no_fail(["mkdir", api_temp])
            execute_no_fail(["mkdir", lambda_temp])
            execute_no_fail(["mkdir", notify_temp])
            Package.package_api(apisource, apiconfig, outdir, api_temp)
            Package.package_notify(apisource, apiconfig, outdir, notify_temp)
            Package.package_lambda(apisource, apiconfig, outdir, lambda_temp)

    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(
                description="Packages the environment for elastic beanstalk in a zip")
        parser.add_argument("config",
                help="the config file to use")
        parser.add_argument("-o", "--outdir", default=".",
                help="The folder to store the zip files")
        args = parser.parse_args()
        Package.package_all(".", args.config, args.outdir)

class DockerPush(object):

    @staticmethod
    def docker_push_list(image_list, tag=None, force=False):
        for image in image_list:
            if tag is not None:
                args = ["docker", "tag", image + ":latest", image + ":" + tag]
                if force:
                    args.append("-f")
                execute_no_fail(args)
            execute_no_fail(["docker", "push", image])

    @staticmethod
    def update_dockerrun_image(filename, image):
        with open(filename, "r") as f:
            dockerrun = json.loads(f.read())
            dockerrun["containerDefinitions"][0]["image"] = image
        with open(filename, "w") as f:
            f.write(json.dumps(dockerrun, indent=4, sort_keys=True))

    @staticmethod
    def docker_deploy(force=False):
        Git.ensure_updated_head()
        tag = Git.get_latest_commit_hash()[:7]
        DockerPush.docker_push_list([
                "delegateit/gatdb",
                "delegateit/gatapi",
                "delegateit/gatntfy"], tag, force)
        DockerPush.update_dockerrun_image("./docker/api/Dockerrun.aws.json", "delegateit/gatapi:" + tag)
        DockerPush.update_dockerrun_image("./docker/notify/Dockerrun.aws.json", "delegateit/gatntfy:" + tag)


    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(
                description="Pushes the images to docker hub and updates the Dockerrun.aws.json files")
        parser.add_argument("-f", "--force",
                help="Image tagging is forced. Will overwrite previous tags")
        args = parser.parse_args()
        DockerPush.docker_deploy(args.force)

class Health(object):
    def display(eb_group):
        cmd =  "tmux new-session -d -s eb-health 'cd docker/api && eb health gator-api-" + eb_group  + " --refresh';"
        cmd += "tmux split-window -v 'cd docker/notify && eb health gator-notify-" + eb_group + " --refresh';"
        cmd += "tmux -2 attach-session -d;"
        execute(cmd, shell=True)


    @staticmethod
    def parse_args():
        env_types = ["live", "test"]
        parser = argparse.ArgumentParser(
                description="Displays the health of the elastic beanstalk environments")
        parser.add_argument("eb_group", choices=env_types,
                help="The type of environment to monitor")
        args = parser.parse_args()
        Health.display(args.eb_group)


class Deploy(object):
    @staticmethod
    def get_commit_hash(apipath):
        print("Making sure api directory has a committed HEAD")

    @staticmethod
    def eb_deploy(modules, eb_group, commit_hash):
        for m in modules:
            env_name = "gator-" + m + "-" + eb_group
            args = ["eb", "deploy", env_name, "-nh"]
            args.extend(["--label", env_name + "-" + commit_hash[:7]])
            args.extend(["--message", "https://github.com/DelegateIt/OrderAPI/commit/" + commit_hash])
            execute(args, cwd=os.path.join(".", "docker", m))

    @staticmethod
    def lambda_deploy(lambda_name, lambda_path):
        execute_no_fail(["aws", "lambda", "update-function-code", "--function-name", lambda_name, "--zip-file", "fileb://" + lambda_path, "--publish"])


    @staticmethod
    def deploy(apipath, apiconfig, eb_group, notify_lambda_name, push_lambda_name):
        Git.ensure_updated_head(apipath)
        commit_hash = Git.get_latest_commit_hash(apipath)
        Package.package_all(apipath, apiconfig, ".")
        print("Deploying commit hash", commit_hash)
        Deploy.eb_deploy(["api", "notify"], eb_group, commit_hash)
        Deploy.lambda_deploy(notify_lambda_name, "./gator-lambda.zip")
        Deploy.lambda_deploy(push_lambda_name, "./gator-lambda.zip")

    @staticmethod
    def parse_args():
        types = {
            "test": {
                "config": "aws-test-config.json",
                "eb-group": "test",
                "notify_lambda": "TestTransactionChange",
                "push_lambda": "TestPushNotifications"
            },
            "live": {
                "config": "aws-prod-config.json",
                "eb-group": "live",
                "notify_lambda": "TransactionUpdate",
                "push_lambda": "PushNotifications"
            }
        }
        parser = argparse.ArgumentParser(
                description="Deploys the code to elastic beanstalk")
        parser.add_argument("deploy_type", choices=types.keys(),
                help="The type of deployment")
        args = parser.parse_args()

        apipath = "."
        deploy_type = types[args.deploy_type]
        apiconfig = os.path.join(apipath, deploy_type["config"])
        Deploy.deploy(apipath, apiconfig, deploy_type["eb-group"], deploy_type["notify_lambda"], deploy_type["push_lambda"])


if __name__ == "__main__":
    actions = {
        "create": {
            "parse": Create.parse_args,
            "description": "create the docker containers and images"
        },
        "start": {
            "parse": Start.parse_args,
            "description": "Starts the api environment"
        },
        "stop": {
            "parse": Stop.parse_args,
            "description": "Stops the api environment"
        },
        "package": {
            "parse": Package.parse_args,
            "description": "Packages the environment for elastic beanstalk in a zip"
        },
        "docker-push": {
            "parse": DockerPush.parse_args,
            "description": "Pushes the images to docker hub and updates the Dockerrun.aws.json files"
        },
        "deploy": {
            "parse": Deploy.parse_args,
            "description": "Deploys the code to elastic beanstalk"
        },
        "health": {
            "parse": Health.parse_args,
            "description": "Displays the health for the elastic beanstalk environment"
        }
    }
    parser = argparse.ArgumentParser(
            description="Helps setup and control the environents for DelegateIt. Possible actions include: " +
            ". ".join([k + " - " + v["description"] for k,v in actions.items()]))
    parser.add_argument("action", choices=actions.keys(), help="The action to perform.")
    parser.add_argument('args', nargs=argparse.REMAINDER,
            help="A list of arguments to pass to the action")


    args = parser.parse_args()
    action_name = sys.argv[1]
    del sys.argv[1]
    sys.argv[0] += " " + args.action
    actions[action_name]["parse"]()
