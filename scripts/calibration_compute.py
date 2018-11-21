#!/usr/bin/env python
# -*- coding: utf-8 -*-

# calibration_compute.py: Code to compute absolute orientation from collected points
# Author: Nishanth Koganti, Ravi Joshi
# Date: 2016/06/16
# Source: http://math.stackexchange.com/questions/745234/calculate-rotation-translation-matrix-to-match-measurement-points-to-nominal-poi

# import modules
import os
import yaml
import rospy
import datetime
import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from tf.transformations import euler_from_matrix, quaternion_from_euler

# matplotlib settings
# matplotlib.rcParams.update({'font.size': 10})
style = 'seaborn-deep'
if style in plt.style.available:
    plt.style.use(style)


def abs_orientation(x, y):
    # number of samples
    n_samples = x.shape[0]

    # center data
    x_mean = x.mean(axis=0)
    y_mean = y.mean(axis=0)

    x_temp = x - x_mean
    y_temp = y - y_mean

    # get the variance
    x_sd = np.mean(np.sum(x_temp**2, 1))
    np.mean(np.sum(y_temp**2, 1))

    # get covariance matrix
    covar_matrix = np.dot(y_temp.T, x_temp) / n_samples

    # apply singular value decomposition
    U, D, V = np.linalg.svd(covar_matrix, full_matrices=True, compute_uv=True)
    V = V.T.copy()

    S = np.diag(np.asarray(
        [1, 1, np.sign(np.linalg.det(V) * np.linalg.det(U))]))

    # get scaling factor
    c = np.trace(np.dot(np.diag(D), S)) / x_sd

    # get rotation matrix
    R = c * np.dot(np.dot(U, S), V.T)

    # get translation vector
    t = y_mean - np.dot(R, x_mean)

    # compute transformation error
    x_out = (np.dot(R, x.T)).T + t
    errs = np.sqrt(np.sum((y - x_out)**2, axis=1))
    return x_out, R, t, errs


def plot_calibration(kinect_out, baxter_traj, kinect, err_cm):
    # plot both point sets together
    fig = plt.figure(1)
    ax = fig.add_subplot(111, projection='3d')

    # plot the data
    ax.scatter(kinect_out[:, 0], kinect_out[:, 1],
               kinect_out[:, 2], s=10, c='r', marker='o', label='Kinect Points')
    ax.scatter(baxter_traj[:, 0], baxter_traj[:, 1],
               baxter_traj[:, 2], s=10, c='b', marker='^', label='Baxter Points')

    # add labels and title
    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_zlabel('z (m)')
    ax.legend()
    ax.grid(True)
    ax.set_title('baxter %s calibration (err: %.2f cm)' %
                 (kinect, err_cm), y=1.1)  # move title little bit up


def plot_error(err, file_name, bar_width=0.35, opacity=0.4):
    fig, ax = plt.subplots()

    err_mm = err * 1000.0  # convert to mm
    x = np.arange(err_mm.shape[0])

    # calculate average of the data
    y_mean = [np.mean(err_mm)] * len(x)

    data_line = ax.bar(x, err_mm, bar_width, alpha=opacity, color='b')
    mean_line = ax.plot(x, y_mean, label='Mean Error: %.2f mm' % y_mean[0],
                        linestyle='--', color='g')

    ticks = np.linspace(start=x[0], stop=x[-1], num=5, dtype=np.int32)
    ticks = (ticks / 10) * 10
    ax.set_xlabel('Points')
    ax.set_ylabel('Error (mm)')
    ax.set_xticks(ticks)
    ax.set_xlim(x[0], x[-1])
    ax.legend()
    ax.set_title('input file: %s' % file_name)


def main():
    # initialize ros node
    rospy.init_node('compute_calibration', anonymous=True)

    # get path to folder containing recorded data
    data_dir = rospy.get_param('~data_dir')
    kinect = rospy.get_param('~kinect')
    ar = rospy.get_param('~ar')

    suffix = 'ar' if ar else 'pc'
    file_name = 'baxter_%s_position_%s.csv' % (kinect, suffix)
    trajectory_file = os.path.join(data_dir, file_name)

    rospy.loginfo('Reading file:\n%s\n' % trajectory_file)

    # load trajectories
    trajectory = np.loadtxt(trajectory_file, delimiter=',', skiprows=1)

    # first three columns belong to baxter trajectories and
    # remaining three columns belong to kinect trajectories
    baxter_traj = trajectory[:, :3]
    kinect_traj = trajectory[:, 3:]

    # compute absolute orientation
    kinect_out, rot, trans, errs = abs_orientation(kinect_traj, baxter_traj)

    # output results
    err = errs.sum() / trajectory.shape[0]
    err_cm = err * 100.0
    rospy.loginfo('Calibration Error: %.2f cm' % err_cm)

    # get rotation matrix as quaternion and euler angles
    euler = euler_from_matrix(rot)
    quat = quaternion_from_euler(*euler)

    # save results to yaml file
    calibration = {'parent': 'base',
                   'child': ('%s_link' % kinect),
                   'trans': trans.tolist(),
                   'rot': quat.tolist(),
                   'rot_euler': list(euler),
                   'calibration error (m)': float('%.4f' % err),
                   'created on': datetime.datetime.now().strftime('%d %B %Y %I:%M:%S %p')}

    with open('%sbaxter_%s_calibration_%s.yaml' % (data_dir, kinect, suffix), 'w') as out_file:
        yaml.dump(calibration, out_file)

    plot_calibration(kinect_out, baxter_traj, kinect, err_cm)
    plot_error(errs, file_name)
    plt.show()


if __name__ == '__main__':
    main()
