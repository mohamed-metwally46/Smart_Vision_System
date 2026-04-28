from roboflow import Roboflow
rf = Roboflow(api_key="fFXhCaoFIFWDvSJAkMWl")
project = rf.workspace("ir-uz1qh").project("weapon-detection-jqd3x")
version = project.version(1)
dataset = version.download("yolov8")