#!/usr/bin/env python
try:
		sys.path.remove('/opt/ros/kinetic/lib/python2.7/dist-packages/')
except:
		pass

import cv2
import numpy as np
import math
import copy
import os

class BullsEyeDetection:
	def __init__(self):
                self.data_path = '/home/abhinav/drone-course/CC_tag_detection/'
                self.thresh = 0.8

	def get_line_clusters(self,np_lines,rho_thresh,theta_thresh):
		line_clusters = []
		while(np_lines.shape[0] != 0):
			comp_theta = np_lines[0,1]
			comp_rho = np_lines[0,0]

			group = np.zeros((1,2))
			count = 0
			for i,[rho, theta] in enumerate(np_lines):
				if abs(comp_theta-theta)<theta_thresh and abs(comp_rho - rho)<rho_thresh:
					group = np.vstack((group,np.array(np_lines[i-count,:])))
					np_lines = np.delete(np_lines,i-count,0)
					count +=1
			group = group[1:,:]
			group_mean = np.mean(group,axis = 0)

			line_clusters.append(group_mean)
		return np.array(line_clusters)

	def augment_lines(self,line_clusters):
		
		rho_arr = line_clusters[:,0]
		i_max = int(np.where(rho_arr == np.amax(rho_arr))[0])
		i_min = int(np.where(rho_arr == np.amin(rho_arr))[0])

		max_line = line_clusters[i_max]
		min_line = line_clusters[i_min]
		line_clusters = np.delete(line_clusters,i_max,0)
		line_clusters = np.delete(line_clusters,i_min-1,0)
		rho_arr = np.delete(rho_arr,i_max,0)
		rho_arr = np.delete(rho_arr,i_min-1,0)
		i_max_2 = int(np.where(rho_arr == np.amax(rho_arr))[0])
		i_min_2 = int(np.where(rho_arr == np.amin(rho_arr))[0])
		sec_max_line = line_clusters[i_max_2]
		sec_min_line = line_clusters[i_min_2]
		sec_max_line[0] = sec_max_line[0]+3
		max_line[0] = max_line[0]-3
		sec_min_line[0] = sec_min_line[0]-3
		min_line[0] = min_line[0]+3
		line_clusters = [max_line,sec_max_line,sec_min_line,min_line]
		
		return line_clusters

	def get_hough_lines(self,edges):
		kernel = np.ones((2,2),np.uint8)
		edges = cv2.dilate(edges,kernel,iterations = 1)
		# cv2.imshow('dilated edges in hough', edges)
		# cv2.waitKey(0)
		# cv2.destroyAllWindows()
		lines = cv2.HoughLines(edges,1,np.pi/120,40)
		lines = np.squeeze(lines)
		edges3CH = np.dstack((edges,edges,edges))
		np_lines=np.array(lines)
		status = False
		line_clusters = self.get_line_clusters(np_lines,25,0.3)
		if(line_clusters.shape[0]>=4):
			mod_line_cluster = self.augment_lines(line_clusters)

			# print ("mod_line_cluster",mod_line_cluster)
			rect_line = np.zeros((1,2))
			
			# print line_clusters
			for rho,theta in mod_line_cluster:
				# rho = rho+1
				a = np.cos(np.float(theta))
				b = np.sin(np.float(theta))
				##### convert line from polar coordinates to cartesian coordinattes
				slope = -a/b
				intercept = rho/b
				# print("intercept, slope = ",intercept,slope)
				rect_line = np.vstack((rect_line,np.array([intercept,slope])))
				x0 = a*rho
				y0 = b*rho
				x1 = int(x0 + 1000*(-b))
				y1 = int(y0 + 1000*(a))
				x2 = int(x0 - 1000*(-b))
				y2 = int(y0 - 1000*(a))
				cv2.line(edges3CH,(x1,y1),(x2,y2),(0,0,255),2)
			rect_line = rect_line[1:,:]
			# print ("rect_line",rect_line)
			# cv2.imshow('edges3CH', edges3CH)
			# cv2.waitKey(0)
			# cv2.destroyAllWindows()
			status = True
			return status,rect_line
		else:
			status = False
			return status,lines


	def refine_contours(self,img,rect_line):
		h,w = img.shape
		mesh = np.mgrid[0:h,0:w]
		# print ("mesh shape = ", mesh.shape)
		rows = mesh[0,:,:]
		cols = mesh[1,:,:]
		# print("row and col shape", rows.shape, cols.shape)
		for i,[intercept,slope] in enumerate(rect_line):
			if(i == 0):
				img[rows-slope*cols-intercept>0] = 0
			if(i == 1):
				img[rows-slope*cols-intercept<0] = 0
			if(i == 2):
				img[rows-slope*cols-intercept>0] = 0
			if(i == 3):
				img[rows-slope*cols-intercept<0] = 0
			
		# intercept0,slope0 = rect_line[0]
		# intercept1,slope1 = rect_line[1]
		# intercept2,slope2 = rect_line[2]
		# intercept3,slope3 = rect_line[3]
		
		# cv2.imshow('removed rectangle', img)
		# cv2.waitKey(0)
		# cv2.destroyAllWindows()
		return img

	def detect_ellipse_fitellipse(self,img):
		gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
		cle = cv2.createCLAHE(clipLimit = 5.0,tileGridSize =(8,8))
		gray = cle.apply(gray)
		## fancy color thresholding	
		img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
		mask = ((img_hsv > np.array([0,0,230])).astype(np.float32) 
				+ (img_hsv > np.array([0,0,230])).astype(np.float32) * (-0.5) + 0.5)

		test_img = np.uint8((mask * img_hsv)*255/np.max(mask * img_hsv))
		img_partly_darken = cv2.cvtColor(test_img, cv2.COLOR_HSV2BGR)
		
		cv2.imshow('contrast corrected', img_partly_darken[:,:,2])
		cv2.waitKey(0)
		cv2.destroyAllWindows()
		max_val = np.amax(gray)
		rand_thresh = gray.copy()
		rand_thresh[rand_thresh[:]<(max_val*self.thresh)] = 0 
		edges = cv2.Canny(rand_thresh,50,150,apertureSize = 3)
		kernel = np.ones((2,2),np.uint8)
		dilated_edges = cv2.dilate(edges,kernel,iterations = 1)
		# cv2.imshow('edges', dilated_edges)
		# cv2.waitKey(0)
		# cv2.destroyAllWindows()
		
		# minLineLength = 40
		# maxLineGap = 100
		# try:
		lines = cv2.HoughLines(edges,1,np.pi/180,30)
		same_thresh = 0.25
		orthogonal_thresh =0.5

		if(lines is not None):
		
			i,contours,h = cv2.findContours(dilated_edges,cv2.RETR_TREE,cv2.CHAIN_APPROX_NONE)
			# print("h = ", h)
			max_w = 0
			max_h = 0
			iter_ = -1
			count = 0
			print("contours",np.shape(contours))
			for i,c1 in enumerate(contours):
				# print i
				# print("c1 = ", c1)
				(x,y,we,he) = cv2.boundingRect(c1)
				# print("bb params = ",x,y,we,he)

				if len(c1)>4 and (we > 10 and he > 10):
						if he>max_h or we>max_w:
							max_h = he
							max_w = we
							iter_=i

						# (cx,cy),(Ma,ma),th = cv2.fitEllipse(c1)
						# print("ellipse = ",(cx,cy),(Ma,ma),th)
						count+=1
			# contours_img = img.copy()
			stencil = np.zeros(edges.shape).astype(edges.dtype)
			color = [255, 255, 255]
			cv2.fillPoly(stencil, contours[iter_], color)
			# result = cv2.bitwise_xor(edges, stencil)
			# cv2.drawContours(stencil, contours[iter_], -1, (0,255,0), 2)
			# cv2.imshow('stencil', stencil)
			# cv2.waitKey(0)
			# cv2.destroyAllWindows()
			hough_status,houg_lines = self.get_hough_lines(stencil)
			if(hough_status):
				refined_contours = self.refine_contours(edges,houg_lines)
				
				# cv2.imshow('refined contours', refined_contours)
				# cv2.waitKey(0)
				# cv2.destroyAllWindows()

				_,contours,h = cv2.findContours(refined_contours,cv2.RETR_TREE,cv2.CHAIN_APPROX_NONE)
				# print("h = ", h)
				max_w = 0
				max_h = 0
				iter_ = -1
				count = 0
				for i,c1 in enumerate(contours):
					(x,y,we,he) = cv2.boundingRect(c1)
					# print("bb params = ",x,y,we,he)

					if len(c1)>4 and (we > 10 and he > 10):
							if he>max_h or we>max_w:
								max_h = he
								max_w = we
								iter_=i

				# fit ellipse now
				(cx,cy),(Ma,ma),th = cv2.fitEllipse(contours[iter_])
				cv2.drawContours(img, contours[iter_], -1, (0,255,0), 2)

				# cv2.imshow('outer ellipse', img)
				# cv2.waitKey(0)
				# cv2.destroyAllWindows()
				print("ellipse = ",(cx,cy),(Ma,ma),th)

			else:
				print("unable to refine")



	def detect_ellipse_hough(self,img):
		kernel = np.ones((3,3),np.uint8)
		gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
		# gray = cv2.medianBlur(gray,5)
		# print("gray shape = ",gray.shape)
		# laplacian = cv2.Laplacian(gray,cv2.CV_64F,ksize = 5)
		# laplacian = cv2.bitwise_not(laplacian)
		max_val = np.amax(gray)
		rand_thresh = gray.copy()
		rand_thresh[rand_thresh[:]<(max_val*self.thresh)] = 0 
		                #cimg = cv2.cvtColor(gray,cv2.COLOR_GRAY2BGR)
		# eroded_img = cv2.erode(rand_thresh,kernel,iterations = 1)
		# edges = cv2.Canny(gray,120,200,apertureSize = 3)
		eroded_img = rand_thresh
		# cv2.imshow('edges', rand_thresh)
		# cv2.waitKey(0)
		# cv2.destroyAllWindows()
		# cv2.imshow('eroded', eroded_img)
		# cv2.waitKey(0)
		# cv2.destroyAllWindows()
		img_three = eroded_img.copy()
		img_three = np.dstack((img_three,eroded_img,eroded_img))
		print("3d img shape = ",img_three.shape)
		circles = cv2.HoughCircles(eroded_img,cv2.HOUGH_GRADIENT,1,10,param1=150,param2=50,minRadius=0,maxRadius=0)
		print("circles = ",circles)
		                #input("aaa")
		if(circles is not None):
				
			circles = np.uint16(np.around(circles))
			circles = np.squeeze(circles)
			print("circle shape = ",circles.shape)
			if (circles.shape[0] == 3):
			        # draw the outer circle
			    cv2.circle(img_three,(circles[0],circles[1]),circles[2],(0,255,0),2)
			    # draw the center of the circle
			    cv2.circle(img_three,(circles[0],circles[1]),2,(0,0,255),3)
			else:

				for i in circles:
				        # draw the outer circle
				    cv2.circle(img_three,(i[0],i[1]),i[2],(0,255,0),2)
				    # draw the center of the circle
				    cv2.circle(img_three,(i[0],i[1]),2,(0,0,255),3)
			# cv2.imshow('circles', img_three)
			# cv2.waitKey(0)
			# cv2.destroyAllWindows()
			# input("ad")
			max_w = 0
			max_h = 0
			iter_ = -1
			count = 0
		else:
			print("no circles detected")
		
		# cv2.imshow('cimg', cimg)
		# cv2.waitKey(0)
		# cv2.destroyAllWindows()

	def run_pipeline(self):
		dirname = sorted(os.listdir(self.data_path))
		for filename in dirname:
		    #print("filename",filename)
		    #print(os.path.join(self.data_path,filename))
		    img = cv2.imread(os.path.join(self.data_path,filename))
		    #cv2.imshow("read img",img)
		#cv2.waitKey(0)
		#cv2.destroyAllWindows()
		    h,w,_ = img.shape
		    #dim = (w/4,h/4)
		    #img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
		    # print("img size = ",img.shape)
		    # self.detect_ellipse_hough(img)
		    self.detect_ellipse_fitellipse(img)


def main():
		ob = BullsEyeDetection()
		ob.run_pipeline()


if __name__ == '__main__':
		main()
