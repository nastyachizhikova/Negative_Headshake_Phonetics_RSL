import pandas as pd
import pympi
import ffmpeg
import os, sys

#  dicts to save additional information to use for graphs building and analysis
video_annotations = {'path': [], 'annotations': []}
fragments_signs = {'fragment': [], 'sign': []}


def cut_one_fragment(start: int, end: int, fragment_name: str, video_name: str, start_off: int, end_off: int):
    print('Extracting fragment ', fragment_name)

    #  save fragments with the same video extension to avoid errors
    if os.path.exists(video_name + '.mp4'):
        video_format = 'mp4'
        input_name = video_name + '.mp4'
    elif os.path.exists(video_name + '.avi'):
        video_format = 'avi'
        input_name = video_name + '.avi'
    elif os.path.exists(video_name + '.AVI'):
        video_format = 'AVI'
        input_name = video_name + '.AVI'
    else:
        print('not found video')

    #  create name for a fragment
    trimmed_name = fragment_name + f'.{video_format}'
    cut_name = f'./annot_cut/{trimmed_name}'

    # cut with ffmpeg
    try:
        (
            ffmpeg
                .input(input_name)
                .trim(start=(start + start_off) / 1000.0, end=(end + end_off)/ 1000.0)
                .setpts('N/(25*TB)')
                .filter('fps', fps=25, round='up')  # all fragments to 25 fps
                .output(cut_name)
                .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise e


def cut_fragment(row):
    '''
    A function to process one sentence fragment from the annotations

    :param row:  row from the dataframe with annotations
    :return: None
    '''
    fragment_name = row['fragment']
    annot = row['annotation']

    start_off = - 80
    end_off = 80
    dir_path = "./annotated_eafs/"

    if str(annot) == '1':  # if there is a hs
        eaf_path = dir_path + fragment_name + '.eaf'
        video_name = dir_path + fragment_name

        #  open eaf-file and get annotated hs boundaries
        eaf = pympi.Elan.Eaf(eaf_path)
        hs_tier = 'nonmanual'
        hs_annots = eaf.get_annotation_data_for_tier(hs_tier)

        #  save hs boundaries to use for graphs visualizing
        video_annotations['path'].append(video_name)
        video_annotations['annotations'].append((hs_annots, start_off, end_off))

        #  for each headshake in the sentence fragment cut fragment and save meta data
        for idx, annot in enumerate(hs_annots):
            if idx > 0:
                fragment_name += f'_{idx}'

            # get manual signs that overlap with headshake
            right_annot = eaf.get_annotation_data_between_times('right', annot[0], annot[1])
            left_annot = eaf.get_annotation_data_between_times('left', annot[0], annot[1])

            #  save their annotations to use in analysis
            fragments_signs['fragment'].append(fragment_name)
            fragments_signs['sign'].append((right_annot, left_annot))

            #  cut one headshake fragment
            cut_one_fragment(annot[0], annot[1], fragment_name, video_name, start_off, end_off)


def process_one_file(filename: str):
    #  open file with fragments annotations
    with open(filename, encoding='utf-8') as f:
        df = pd.read_csv(f, sep=';')

    #  process each fragment
    df.apply(lambda x: cut_fragment(x), axis=1)


def main():
    process_one_file('annotations.csv')

    # save meta data
    df = pd.DataFrame(video_annotations)
    df.to_csv('video_annotations.csv')

    df = pd.DataFrame(fragments_signs)
    df.to_csv('sign_annotations.csv')


if __name__ == '__main__':
    main()

