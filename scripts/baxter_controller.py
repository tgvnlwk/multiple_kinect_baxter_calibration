#!/usr/bin/env python

import rospy
import numpy as np
from baxter_interface import Limb
from std_msgs.msg import Bool, Int8


class BaxterController():
    def __init__(self, wait_time, limb, file_name):
        trajectory_index = 0
        baxter_moving = 0 # moving:0, stop:1, finished:2
        self.data_collection_happening = False

        wait_time = int(wait_time)
        arm = Limb(limb)
        joint_names = arm.joint_names()
        trajectory = np.loadtxt(file_name, delimiter=',', skiprows=1)

        baxter_status_pub = rospy.Publisher('baxter_arm_motion_status', Int8, queue_size=10)
        rospy.Subscriber('is_data_collection_happening', Bool, self.callback)

        #rospy.sleep(wait_time)
        while not rospy.is_shutdown():
            if trajectory_index >= trajectory.shape[0]:
                baxter_moving = 2  # moving:0, stop:1, finished:2
                baxter_status_pub.publish(baxter_moving)
                rospy.loginfo('Baxter arm trajectory finished. Exiting now...')
                break

            if not self.data_collection_happening:
                baxter_moving = 0
                baxter_status_pub.publish(baxter_moving)
                joint_values = trajectory[trajectory_index, :]
                joint_command = dict(zip(joint_names, joint_values))
                arm.move_to_joint_positions(joint_command)
                rospy.sleep(wait_time)
                trajectory_index += 1

            baxter_moving = 1  # moving:0, stop:1, finished:2
            baxter_status_pub.publish(baxter_moving)
            rospy.sleep(0.1)  # sleep for 100 ms

    def callback(self, msg):
        self.data_collection_happening = msg.data


if __name__ == '__main__':
    rospy.init_node('baxter_controller_node', anonymous=True)

    limb = rospy.get_param('~limb')
    wait_time = rospy.get_param('~wait_time')
    file_name = rospy.get_param('~trajectory')

    BaxterController(wait_time, limb, file_name)