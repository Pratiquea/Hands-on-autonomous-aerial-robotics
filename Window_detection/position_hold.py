#!/usr/bin/env python

import cv2
import numpy as np
import math
import matplotlib.pyplot as plt
import rospy
import time
from std_msgs.msg import Empty
from geometry_msgs.msg import Twist, Pose
from nav_msgs.msg import Odometry
# from GMM.test_data import *
# from sensor_msgs.msg import Image
# from cv_bridge import CvBridge, CvBridgeError

class moveit:
	def __init__(self):
		self.odom_sub = rospy.Subscriber('/bebop/odom', Odometry, self.odom_callback)
		self.takeoff_pub = rospy.Publisher('/bebop/takeoff', Empty, queue_size=1 , latch=True)
		self.bebop_vel_pub = rospy.Publisher('/bebop/cmd_vel', Twist, queue_size=10)
		self.land_pub = rospy.Publisher('/bebop/land', Empty, queue_size=1 , latch=True)
		self.vel_sp_sub = rospy.Subscriber('/cmd_vel_setpoint', Pose, self.vel_sp_cb)
		self.cam_pose_sub = rospy.Subscriber('/relative_pose',Twist,self.cam_pose_cb)

		self.inFlight = False
		self.pose = Pose()
		# self.twist = Twist()
		self.bias = np.zeros((6,))
		self.velocity_msg = Twist()
		self.areas = []
		self.odom_list = []
		self.dt = 0.1
		self.inFlight = False
		self.vel_pub_rate = rospy.Rate(10)
		self.vel_sp = np.zeros((6,))
		self.vel_sp[2] = 1.0
		self.current_state = np.zeros((6,))
		self.x_sp = 0
		self.y_sp = 0
		self.z_sp = 0
		self.yaw_sp = 0
		self.min_step = 0.0
		self.max_step = 0.4
		self.Kp = [0.05,0.05,0.08,0.0,0.0,0.01]


	def cam_pose_cb(self,data):
		print("campose cb", data.linear.x)
		self.x_sp = data.linear.x
		self.y_sp = data.linear.y
		self.z_sp = data.linear.z
		self.yaw_sp = data.angular.z

	def vel_sp_cb(self,data):
		self.vel_sp[0] = -data.position.x
		self.vel_sp[1] = data.position.y
		self.vel_sp[2] = data.position.z
		self.vel_sp[3] = data.orientation.x
		self.vel_sp[4] = data.orientation.y
		self.vel_sp[5] = data.orientation.z

	def orient(self, twist_msg):
		self.velocity_msg = twist_msg
		self.bebop_vel_pub.publish(self.velocity_msg)

	def calculate_bias(self):
		self.bias[0] = self.pose.position.x
		self.bias[1] = self.pose.position.y
		self.bias[2] = self.pose.position.z
		self.bias[3] = self.pose.orientation.x
		self.bias[4] = self.pose.orientation.y
		self.bias[5] = self.pose.orientation.z
		
	def takeoff(self):
		self.takeoff_pub.publish()
		self.inFlight = True

	def land(self):
		self.land_pub.publish()
		self.inFlight = False

	def odom_callback(self, data):
		self.pose = data.pose.pose
		# print "pose ", self.pose
		# self.Twist = data.twist.twist
		self.current_state[0] = data.pose.pose.position.x
		self.current_state[1] = data.pose.pose.position.y
		self.current_state[2] = data.pose.pose.position.z
		self.current_state[3] = data.pose.pose.orientation.x
		self.current_state[4] = data.pose.pose.orientation.y
		self.current_state[5] = data.pose.pose.orientation.z
		self.odom_data = data
		# print("odom linear, is it array?", data.pose.pose.position)
		# print "twist ", self.Twist

	# def xline(self):

	# 	vel = Twist()
	# 	ref = self.vel_sp
	# 	dt = 0.1
	# 	t = 0
	# 	while ((not rospy.is_shutdown()) and t <0.5):
			
	# 		vel.linear.x = 0
	# 		vel.linear.y = 0
	# 		vel.linear.z = dt*4

	# 		vel.angular.x = 0
	# 		vel.angular.y = 0
	# 		vel.angular.z = 0

	# 		# print("angular z = ", vel.angular.z)
	# 		self.orient(vel)
	# 		# print("t = ",t)
	# 		t+=dt
	# 		self.vel_pub_rate.sleep()

	def move(self,ref):

		vel = Twist()
		# ref = self.vel_sp
		# dt = 0.1
			# print("reference state = ", ref[:3])
		while ((not rospy.is_shutdown())):
			# print("current_state = ", abs_curr_state[:3])
			# err = ref + abs_curr_state

			print("ref = ", ref)
			current_abs_state = self.current_state - self.bias
			print("biased compensated state",current_abs_state)
			err_x = -ref[0] - current_abs_state[0]
			vel_arr_x = self.Kp[0]*err_x
			
			print("vel x: ",vel_arr_x)		
			err_y = ref[1] - current_abs_state[1]
			vel_arr_y = self.Kp[1]*err_y
			print("vel y",vel_arr_y)
			err_z = ref[2] - current_abs_state[2]
			vel_arr_z = self.Kp[2]*err_z
			
			print("vel z: ",vel_arr_z)
					
			err_yaw = -ref[-1] + current_abs_state[-1]
			#print("err = ", err[:3])
			vel_arr_yaw = self.Kp[-1]*err_x
			print("vel yaw",vel_arr_yaw)
			# print("vel = ", vel_arr[:3])

			vel.linear.x = vel_arr_x
			vel.linear.y = vel_arr_y
			vel.linear.z = vel_arr_z

			vel.angular.x = 0
			vel.angular.y = 0
			vel.angular.z = vel_arr_yaw
			# print("angular z = ", vel.angular.z)
			self.orient(vel)
			# print("t = ",t)
			# t+=dt
			self.vel_pub_rate.sleep()

	def iLikeToMoveItMoveIt(self):
		ref = np.array([self.x_sp,self.y_sp,self.z_sp,self.yaw_sp])
		while (not rospy.is_shutdown()):
			print(ref)
			self.move(ref)
			print("moving")
# def land_out():


def main():
	rospy.init_node('position_hold', anonymous=True)
	pos_hld = moveit()
	pos_hld.takeoff()
	time.sleep(3)
	pos_hld.calculate_bias()
	time.sleep(2)
	pos_hld.iLikeToMoveItMoveIt()
	# pos_hld.xline()
	# rospy.on_shutdown(pid.land())

if __name__ == '__main__':
	main()
